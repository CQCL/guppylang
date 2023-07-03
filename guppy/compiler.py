import ast
import inspect
import sys
import textwrap
from abc import ABC
from dataclasses import dataclass
from typing import Iterator, Optional, Any, Callable, Union

from guppy.cfg import CFG, BB, return_var, CFGBuilder
from guppy.guppy_types import (
    GuppyType,
    type_from_python_value,
    IntType,
    FloatType,
    BoolType,
    FunctionType,
    TupleType,
    SumType,
    TypeRow,
    StringType,
)
from guppy.hugr.hugr import OutPortV, Hugr, DFContainingNode, Node, BlockNode, CFNode
from guppy.util import (
    Assign,
    GuppyError,
    assert_arith_type,
    assert_bool_type,
    assert_int_type,
    InternalGuppyError,
    GuppyTypeError,
    AstNode,
    SourceLoc,
    UndefinedPort,
)
from guppy.visitor import AstVisitor
from guppy.visualise import render_cfg


@dataclass(frozen=True)
class RawVariable:
    """Class holding data associated with a variable.

    Besides the name and type, we also store a set of assign statements where the
    variable was defined."""

    name: str
    ty: GuppyType
    defined_at: set[Assign]

    def __lt__(self, other: "Variable") -> bool:
        return self.name < other.name


@dataclass(frozen=True)
class Variable(RawVariable):
    """Represents a concrete variable during compilation.

    Compared to a `RawVariable`, each variable corresponds to a Hugr port.
    """

    port: OutPortV

    def __init__(self, name: str, port: OutPortV, defined_at: set[Assign]):
        super().__init__(name, port.ty, defined_at)
        object.__setattr__(self, "port", port)


# A dictionary mapping names to live variables
VarMap = dict[str, Variable]

# Signature of a basic block
Signature = list[RawVariable]


@dataclass
class DFContainer:
    """A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores the node
    whose dataflow child-graph is currently being constructed as well as all live
    variables. Note that the variable map is mutated in-place and always reflects the
    current compilation state.
    """

    node: DFContainingNode
    variables: VarMap

    def __getitem__(self, item: str) -> Variable:
        return self.variables[item]

    def __setitem__(self, key: str, value: Variable) -> None:
        self.variables[key] = value

    def __iter__(self) -> Iterator[Variable]:
        return iter(self.variables.values())

    def __contains__(self, item: str) -> bool:
        return item in self.variables

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.node, self.variables.copy())

    def get_var(self, name: str) -> Optional[Variable]:
        return self.variables.get(name, None)


def expr_to_row(expr: ast.expr) -> list[ast.expr]:
    """Turns an expression into a row expressions by unpacking top-level tuples."""
    return expr.elts if isinstance(expr, ast.Tuple) else [expr]


def type_from_ast(node: ast.expr) -> GuppyType:
    """Turns an AST expression into a Guppy type."""
    if isinstance(node, ast.Name):
        if node.id == "int":
            return IntType()
        elif node.id == "float":
            return FloatType()
        elif node.id == "bool":
            return BoolType()
        elif node.id == "str":
            return StringType()
    elif isinstance(node, ast.Tuple):
        return TupleType([type_from_ast(el) for el in node.elts])
    # TODO: Remaining cases
    raise GuppyError(f"Invalid type: `{ast.unparse(node)}`", node)


def type_row_from_ast(node: ast.expr) -> TypeRow:
    """Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(value=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeRow([])
    return TypeRow([type_from_ast(e) for e in expr_to_row(node)])


class CompilerBase(ABC):
    """Base class for the Guppy compiler.

    Provides utility methods for working with inputs, outputs, DFGs, and blocks.
    """

    graph: Hugr
    global_variables: VarMap


class ExpressionCompiler(CompilerBase, AstVisitor[OutPortV]):
    """A compiler from Python expressions to Hugr."""

    dfg: DFContainer

    def __init__(self, graph: Hugr):
        self.graph = graph

    def compile(self, expr: ast.expr, dfg: DFContainer) -> OutPortV:
        """Compiles an expression and returns a single port holding the output value."""
        self.dfg = dfg
        with self.graph.parent(dfg.node):
            res = self.visit(expr)
        return res

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[OutPortV]:
        """Compiles a row expression and returns a list of ports, one for
        each value in the row.

        On Python-level, we treat tuples like rows on top-level. However,
        nested tuples are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Expression not supported", node)

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        if type_from_python_value(node.value) is None:
            raise GuppyError("Unsupported constant expression", node)
        return self.graph.add_constant(node.value).out_port(0)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        x = node.id
        if x in self.dfg or x in self.global_variables:
            var = self.dfg.get_var(x) or self.global_variables[x]
            return var.port
        raise GuppyError(f"Variable `{x}` is not defined", node)

    def visit_JoinedString(self, node: ast.JoinedStr) -> OutPortV:
        raise GuppyError("Guppy does not support formatted strings", node)

    def visit_Tuple(self, node: ast.Tuple) -> OutPortV:
        return self.graph.add_make_tuple(
            inputs=[self.visit(e) for e in node.elts]
        ).out_port(0)

    def visit_List(self, node: ast.List) -> OutPortV:
        raise NotImplementedError()

    def visit_Set(self, node: ast.Set) -> OutPortV:
        raise NotImplementedError()

    def visit_Dict(self, node: ast.Dict) -> OutPortV:
        raise NotImplementedError()

    def visit_UnaryOp(self, node: ast.UnaryOp) -> OutPortV:
        port = self.visit(node.operand)
        ty = port.ty
        if isinstance(node.op, ast.UAdd):
            assert_arith_type(ty, node.operand)
            return port  # Unary plus is a noop
        elif isinstance(node.op, ast.USub):
            assert_arith_type(ty, node.operand)
            func = "ineg" if isinstance(ty, IntType) else "fneg"
            return self.graph.add_arith(func, inputs=[port], out_ty=ty).out_port(0)
        elif isinstance(node.op, ast.Not):
            assert_bool_type(ty, node.operand)
            return self.graph.add_arith("not", inputs=[port], out_ty=ty).out_port(0)
        elif isinstance(node.op, ast.Invert):
            # The unary invert operator `~` is defined as `~x = -(x + 1)` and only valid
            # for integer types.
            # See https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations
            # TODO: Do we want to follow the Python definition or have a custom HUGR op?
            assert_int_type(ty, node.operand)
            one = self.graph.add_constant(1)
            inc = self.graph.add_arith(
                "iadd", inputs=[port, one.out_port(0)], out_ty=ty
            )
            inv = self.graph.add_arith("ineg", inputs=[inc.out_port(0)], out_ty=ty)
            return inv.out_port(0)
        else:
            raise InternalGuppyError(
                f"Unexpected unary operator encountered: {node.op}"
            )

    def binary_arith_op(
        self,
        left: OutPortV,
        left_expr: ast.expr,
        right: OutPortV,
        right_expr: ast.expr,
        int_func: str,
        float_func: str,
        bool_out: bool,
    ) -> OutPortV:
        """Helper function for compiling binary arithmetic operations."""
        assert_arith_type(left.ty, left_expr)
        assert_arith_type(right.ty, right_expr)
        # Automatic coercion from `int` to `float` if one of the operands is `float`
        is_float = isinstance(left.ty, FloatType) or isinstance(right.ty, FloatType)
        if is_float:
            if isinstance(left.ty, IntType):
                left = self.graph.add_arith(
                    "int_to_float", inputs=[left], out_ty=FloatType()
                ).out_port(0)
            if isinstance(right.ty, IntType):
                right = self.graph.add_arith(
                    "int_to_float", inputs=[right], out_ty=IntType()
                ).out_port(0)
        return_ty = (
            BoolType() if bool_out else left.ty
        )  # At this point we have `left.ty == right.ty`
        node = self.graph.add_arith(
            float_func if is_float else int_func, inputs=[left, right], out_ty=return_ty
        )
        return node.out_port(0)

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return self.binary_arith_op(
                left, node.left, right, node.right, "iadd", "fadd", False
            )
        elif isinstance(node.op, ast.Sub):
            return self.binary_arith_op(
                left, node.left, right, node.right, "isub", "fsub", False
            )
        elif isinstance(node.op, ast.Mult):
            return self.binary_arith_op(
                left, node.left, right, node.right, "imul", "fmul", False
            )
        elif isinstance(node.op, ast.Div):
            return self.binary_arith_op(
                left, node.left, right, node.right, "idiv", "fdiv", False
            )
        elif isinstance(node.op, ast.Mod):
            return self.binary_arith_op(
                left, node.left, right, node.right, "imod", "fmod", False
            )
        elif isinstance(node.op, ast.Pow):
            return self.binary_arith_op(
                left, node.left, right, node.right, "ipow", "fpow", False
            )
        else:
            raise GuppyError(f"Binary operator `{node.op}` is not supported", node.op)

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
        # Support chained comparisons, e.g. `x <= 5 < y` by compiling to
        # `and(x <= 5, 5 < y)`
        def compile_comparisons() -> Iterator[OutPortV]:
            left_expr = node.left
            left = self.visit(left_expr)
            for right_expr, op in zip(node.comparators, node.ops):
                right = self.visit(right_expr)
                if isinstance(op, ast.Eq) or isinstance(op, ast.Is):
                    # TODO: How is equality defined? What can the operators be?
                    yield self.graph.add_arith(
                        "eq", inputs=[left, right], out_ty=BoolType()
                    ).out_port(0)
                elif isinstance(op, ast.NotEq) or isinstance(op, ast.IsNot):
                    yield self.graph.add_arith(
                        "neq", inputs=[left, right], out_ty=BoolType()
                    ).out_port(0)
                elif isinstance(op, ast.Lt):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "ilt", "flt", True
                    )
                elif isinstance(op, ast.LtE):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "ileq", "fleq", True
                    )
                elif isinstance(op, ast.Gt):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "igt", "fgt", True
                    )
                elif isinstance(op, ast.GtE):
                    yield self.binary_arith_op(
                        left, left_expr, right, right_expr, "igeg", "fgeg", True
                    )
                else:
                    # Remaining cases are `in`, and `not in`.
                    # TODO: We want to support this once collections are added
                    raise GuppyError(
                        f"Binary operator `{ast.unparse(op)}` is not supported", op
                    )
                left = right
                left_expr = right_expr

        acc, *rest = list(compile_comparisons())
        for port in rest:
            acc = self.graph.add_arith(
                "and", inputs=[acc, port], out_ty=BoolType()
            ).out_port(0)
        return acc

    def visit_BoolOp(self, node: ast.BoolOp) -> OutPortV:
        if isinstance(node.op, ast.And):
            func = "and"
        elif isinstance(node.op, ast.Or):
            func = "or"
        else:
            raise InternalGuppyError(f"Unexpected BoolOp encountered: {node.op}")
        operands = [self.visit(operand) for operand in node.values]
        acc = operands[0]
        for operand in operands[1:]:
            acc = self.graph.add_arith(
                func, inputs=[acc, operand], out_ty=BoolType()
            ).out_port(0)
        return acc

    def visit_Call(self, node: ast.Call) -> OutPortV:
        # We need to figure out if this is a direct or indirect call
        f = node.func
        if (
            isinstance(f, ast.Name)
            and f.id in self.global_variables
            and f.id not in self.dfg
        ):
            is_direct = True
            var = self.global_variables[f.id]
            func_port = var.port
        else:
            is_direct = False
            func_port = self.visit(f)

        func_ty = func_port.ty
        if not isinstance(func_ty, FunctionType):
            raise GuppyTypeError(f"Expected function type, got `{func_ty}`", f)
        if len(node.keywords) > 0:
            # TODO: Implement this
            raise GuppyError(
                f"Argument passing by keyword is not supported", node.keywords[0]
            )
        exp, act = len(func_ty.args), len(node.args)
        if act < exp:
            raise GuppyTypeError(
                f"Not enough arguments passed (expected {exp}, got {act})", node
            )
        if exp < act:
            raise GuppyTypeError(f"Unexpected argument", node.args[exp])

        args = [self.visit(arg) for arg in node.args]
        for i, port in enumerate(args):
            if port.ty != func_ty.args[i]:
                raise GuppyTypeError(
                    f"Expected argument of type `{func_ty.args[i]}`, got `{port.ty}`",
                    node.args[i],
                )

        if is_direct:
            call = self.graph.add_call(func_port, args)
        else:
            call = self.graph.add_indirect_call(func_port, args)

        # Group outputs into tuple
        returns = [call.out_port(i) for i in range(len(func_ty.returns))]
        if len(returns) != 1:
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        return returns[0]


@dataclass
class CompiledBB:
    node: CFNode
    bb: BB
    # TODO: Refactor: Turn `Signature` into dataclass with `input` and `outputs`
    input_sig: Signature
    output_sigs: list[Signature]  # One for each successor


class BBCompiler(CompilerBase, AstVisitor[None]):
    expr_compiler: ExpressionCompiler
    return_tys: list[GuppyType]

    def __init__(self, graph: Hugr):
        self.graph = graph
        self.expr_compiler = ExpressionCompiler(graph)

    def _make_predicate_output(
        self, pred: OutPortV, output_vars: list[set[str]], dfg: DFContainer
    ) -> OutPortV:
        """Selects an output based on a predicate.

        Given `pred: Sum((), (), ...)` and output variable sets `#s1, #s2, ...`,
        constructs a predicate value of type `Sum(Tuple(#s1), Tuple(#s2), ...)`.
        """
        assert isinstance(pred.ty, SumType) and len(pred.ty.element_types) == len(
            output_vars
        )
        tuples = [
            self.graph.add_make_tuple(
                inputs=[dfg[x].port for x in sorted(vs) if x in dfg], parent=dfg.node
            ).out_port(0)
            for vs in output_vars
        ]
        tys = [t.ty for t in tuples]
        conditional = self.graph.add_conditional(
            cond_input=pred, inputs=tuples, parent=dfg.node
        )
        for i, ty in enumerate(tys):
            case = self.graph.add_case(conditional)
            inp = self.graph.add_input(output_tys=tys, parent=case).out_port(i)
            tag = self.graph.add_tag(
                variants=tys, tag=i, inp=inp, parent=case
            ).out_port(0)
            self.graph.add_output(inputs=[tag], parent=case)
        return conditional.add_out_port(SumType([t.ty for t in tuples]))

    def compile(
        self, bb: BB, sig: Signature, return_tys: list[GuppyType], parent: Node
    ) -> CompiledBB:
        # The exit BB is completely empty
        if len(bb.successors) == 0:
            block = self.graph.add_exit(return_tys, parent)
            return CompiledBB(block, bb, sig, [])

        self.return_tys = return_tys
        block = self.graph.add_block(parent)
        inp = self.graph.add_input(output_tys=[v.ty for v in sig], parent=block)
        dfg = DFContainer(
            block,
            {
                v.name: Variable(v.name, inp.out_port(i), v.defined_at)
                for (i, v) in enumerate(sig)
            },
        )

        for node in bb.statements:
            self.visit(node, dfg)

        outputs = [dfg[x].port for x in bb.successors[0].vars.live_before if x in dfg]

        # If the BB branches, we have to compile the branch predicate
        if len(bb.successors) > 1:
            assert bb.branch_pred is not None
            branch_port = self.expr_compiler.compile(bb.branch_pred, dfg)
            # If the branches use different variables, we have to use the predicate
            # output feature.
            if any(
                s.vars.live_before.keys() != bb.successors[0].vars.live_before.keys()
                for s in bb.successors[1:]
            ):
                branch_port = self._make_predicate_output(
                    pred=branch_port,
                    output_vars=[
                        set(succ.vars.live_before.keys()) for succ in bb.successors
                    ],
                    dfg=dfg,
                )
                outputs = []
        # Even if the BB doesn't branch, we still have to add a unit `Sum(())` predicate
        else:
            unit = self.graph.add_make_tuple([], parent=block).out_port(0)
            branch_port = self.graph.add_tag(
                variants=[TupleType([])], tag=0, inp=unit, parent=block
            ).out_port(0)

        self.graph.add_output(inputs=[branch_port] + outputs, parent=block)

        return CompiledBB(
            block,
            bb,
            sig,
            [[dfg[x] for x in succ.vars.live_before if x in dfg] for succ in bb.successors],
        )

    def visit_Assign(self, node: ast.Assign, dfg: DFContainer) -> None:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            raise GuppyError("Multi assignment not supported", node)
        target = node.targets[0]
        row = self.expr_compiler.compile_row(node.value, dfg)
        if len(row) == 0:
            # In Python it's fine to assign a void return with the variable being bound
            # to `None` afterward. At the moment, we don't have a `None` type in Guppy,
            # so we raise an error for now.
            # TODO: Think about this. Maybe we should uniformly treat `None` as the
            #  empty tuple?
            raise GuppyError("Cannot unpack empty row")
        assert len(row) > 0

        # Helper function to unpack the row based on the LHS pattern
        def unpack(pattern: AstNode, ports: list[OutPortV]) -> None:
            # Easiest case is if the LHS pattern is a single variable. Note we
            # implicitly pack the row into a tuple if it has more than one element.
            # I.e. `x = 1, 2` works just like `x = (1, 2)`.
            if isinstance(pattern, ast.Name):
                port = (
                    ports[0]
                    if len(ports) == 1
                    else self.graph.add_make_tuple(
                        inputs=ports, parent=dfg.node
                    ).out_port(0)
                )
                dfg[pattern.id] = Variable(pattern.id, port, {node})
            # The only other thing we support right now are tuples
            elif isinstance(pattern, ast.Tuple):
                if len(ports) == 1 and isinstance(ports[0].ty, TupleType):
                    ports = list(
                        self.graph.add_unpack_tuple(
                            input_tuple=ports[0], parent=dfg.node
                        ).out_ports
                    )
                n, m = len(pattern.elts), len(ports)
                if n != m:
                    raise GuppyTypeError(
                        f"{'Too many' if n < m else 'Not enough'} "
                        f"values to unpack (expected {n}, got {m})",
                        node,
                    )
                for pat, port in zip(pattern.elts, ports):
                    unpack(pat, [port])
            # TODO: Python also supports assignments like `[a, b] = [1, 2]` or
            #  `a, *b = ...`. The former would require some runtime checks but
            #  the latter should be easier to do (unpack and repack the rest).
            else:
                raise GuppyError("Assignment pattern not supported", pattern)

        unpack(target, row)

    def visit_AnnAssign(self, node: ast.AnnAssign, dfg: DFContainer) -> None:
        # TODO: Figure out what to do with type annotations
        raise NotImplementedError()

    def visit_AugAssign(self, node: ast.AugAssign, dfg: DFContainer) -> None:
        # TODO: Set all source location attributes
        bin_op = ast.BinOp(left=node.target, op=node.op, right=node.value)
        assign = ast.Assign(
            targets=[node.target],
            value=bin_op,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )
        self.visit_Assign(assign, dfg)

    def visit_Return(self, node: ast.Return, dfg: DFContainer) -> None:
        if node.value is None:
            row = []
        else:
            port = self.expr_compiler.compile(node.value, dfg)
            # Top-level tuples are unpacked, i.e. turned into a row
            if isinstance(port.ty, TupleType):
                unpack = self.graph.add_unpack_tuple(port, dfg.node)
                row = [unpack.out_port(i) for i in range(len(port.ty.element_types))]
            else:
                row = [port]

        tys = [p.ty for p in row]
        if tys != self.return_tys:
            raise GuppyTypeError(
                f"Return type mismatch: expected `{TypeRow(self.return_tys)}`, "
                f"got `{TypeRow(tys)}`",
                node.value,
            )

        # We turn returns into assignments of dummy variables, i.e. the statement
        # `return e0, e1, e2` is turned into `%ret0 = e0; %ret1 = e1; %ret2 = e2`.
        for i, port in enumerate(row):
            name = return_var(i)
            dfg[name] = Variable(name, port, set())


class CFGCompiler(CompilerBase):
    bb_compiler: BBCompiler

    def __init__(self, graph: Hugr) -> None:
        self.graph = graph
        self.bb_compiler = BBCompiler(graph)

    def compile(
        self,
        cfg: CFG,
        input_sig: Signature,
        exp_return_tys: list[GuppyType],
        parent: Node,
    ) -> None:
        compiled: dict[BB, CompiledBB] = {}

        entry_compiled = self.bb_compiler.compile(
            cfg.entry_bb, input_sig, exp_return_tys, parent
        )
        compiled[cfg.entry_bb] = entry_compiled

        # Visit all control-flow edges in BFS order
        stack = [
            (entry_compiled, entry_compiled.output_sigs[i], succ)
            # Put successors onto stack in reverse order to maintain the original order
            # when popping
            for i, succ in reversed(list(enumerate(cfg.entry_bb.successors)))
        ]
        while len(stack) > 0:
            pred, sig, bb = stack.pop()

            # If the BB was already compiled, we just have to check that the signatures
            # match.
            if bb in compiled:
                assert len(sig) == len(compiled[bb].input_sig)
                for v1, v2 in zip(sig, compiled[bb].input_sig):
                    assert v1.name == v2.name
                    if v1.ty != v2.ty:
                        f1 = [f"{{{i}}}" for i in range(len(v1.defined_at))]
                        f2 = [f"{{{len(f1) + i}}}" for i in range(len(v2.defined_at))]
                        raise GuppyError(
                            f"Variable `{v1.name}` can refer to different types: "
                            f"`{v1.ty}` (at {', '.join(f1)}) vs "
                            f"`{v2.ty}` (at {', '.join(f2)})",
                            bb.vars.live_before[v1.name],
                            list(sorted(v1.defined_at)) + list(sorted(v2.defined_at)),
                        )
                self.graph.add_edge(
                    pred.node.add_out_port(), compiled[bb].node.in_port(None)
                )

            # Otherwise, compile the BB and put successors on the stack
            else:
                bb_compiled = self.bb_compiler.compile(bb, sig, exp_return_tys, parent)
                self.graph.add_edge(
                    pred.node.add_out_port(), bb_compiled.node.in_port(None)
                )
                compiled[bb] = bb_compiled
                stack += [
                    (bb_compiled, bb_compiled.output_sigs[i], succ)
                    # Put successors onto stack in reverse order to maintain the
                    # original order when popping
                    for i, succ in reversed(list(enumerate(bb.successors)))
                ]


@dataclass
class GuppyFunction:
    """Class holding all information associated with a Function during compilation."""

    name: str
    module: "GuppyModule"
    def_node: Node
    ty: FunctionType
    ast: ast.FunctionDef

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # The `@guppy` annotator returns a `GuppyFunction`. If the user tries to call
        # it, we can give a nice error message:
        raise GuppyError("Guppy functions can only be called inside of Guppy functions")


class FunctionCompiler(CompilerBase):
    cfg_builder: CFGBuilder
    cfg_compiler: CFGCompiler

    def __init__(self, graph: Hugr):
        self.graph = graph
        self.cfg_builder = CFGBuilder()
        self.cfg_compiler = CFGCompiler(graph)

    @staticmethod
    def validate_signature(func_def: ast.FunctionDef) -> FunctionType:
        """Checks the signature of a function definition and returns the corresponding
        Guppy type."""
        if len(func_def.args.posonlyargs) != 0:
            raise GuppyError(
                "Positional-only parameters not supported", func_def.args.posonlyargs[0]
            )
        if len(func_def.args.kwonlyargs) != 0:
            raise GuppyError(
                "Keyword-only parameters not supported", func_def.args.kwonlyargs[0]
            )
        if func_def.args.vararg is not None:
            raise GuppyError("*args not supported", func_def.args.vararg)
        if func_def.args.kwarg is not None:
            raise GuppyError("**kwargs not supported", func_def.args.kwarg)
        if func_def.returns is None:
            raise GuppyError(
                "Return type must be annotated", func_def
            )  # TODO: Error location is incorrect

        arg_tys = []
        arg_names = []
        for i, arg in enumerate(func_def.args.args):
            if arg.annotation is None:
                raise GuppyError("Argument type must be annotated", arg)
            ty = type_from_ast(arg.annotation)
            arg_tys.append(ty)
            arg_names.append(arg.arg)

        ret_type_row = type_row_from_ast(func_def.returns)
        return FunctionType(arg_tys, ret_type_row.tys, arg_names)

    def compile(
        self,
        module: "GuppyModule",
        func_def: ast.FunctionDef,
        def_node: Node,
        global_variables: VarMap,
    ) -> GuppyFunction:
        self.global_variables = global_variables
        self.cfg_compiler.global_variables = global_variables
        self.cfg_compiler.bb_compiler.global_variables = global_variables
        self.cfg_compiler.bb_compiler.expr_compiler.global_variables = global_variables
        func_ty = self.validate_signature(func_def)
        args = func_def.args.args
        arg_names = set(a.arg for a in args)

        cfg = self.cfg_builder.build(func_def.body, len(func_ty.returns))
        cfg.analyze_liveness()
        cfg.analyze_definite_assignment()

        # Live variables before the entry BB correspond to usages without prior
        # assignment
        for x, use_bb in cfg.entry_bb.vars.live_before.items():
            # Functions arguments and global variables are fine
            if x in arg_names or x in self.global_variables:
                continue
            # The rest results in an error. If the variable is defined on *some* paths,
            # we can give a more informative error message
            if any(
                x in p.vars.assigned_before or x in p.vars.assigned for p in use_bb.predecessors
            ):
                # TODO: Can we point to the actual path in the message in a nice way?
                raise GuppyError(
                    f"The variable `{x}` is not defined on all control-flow paths",
                    use_bb.vars.used[x],
                )
            else:
                GuppyError(f"Variable `{x}` is not defined", use_bb.vars.used[x])

        render_cfg(cfg, "cfg")

        def_input = self.graph.add_input(parent=def_node)
        cfg_node = self.graph.add_cfg(
            def_node, inputs=[def_input.add_out_port(ty) for ty in func_ty.args]
        )
        input_sig = [
            RawVariable(x, t, l)
            for x, t, l in zip(func_ty.arg_names, func_ty.args, args)
        ]
        self.cfg_compiler.compile(cfg, input_sig, list(func_ty.returns), cfg_node)

        # Add final output node for the def block
        self.graph.add_output(
            inputs=[cfg_node.add_out_port(ty) for ty in func_ty.returns],
            parent=def_node,
        )

        return GuppyFunction(func_def.name, module, def_node, func_ty, func_def)


def format_source_location(
    source_lines: list[str],
    loc: Union[ast.AST, ast.operator, ast.expr, ast.arg, ast.Name],
    line_offset: int,
    num_lines: int = 3,
    indent: int = 4,
) -> str:
    """Creates a pretty banner to show source locations for errors."""
    assert loc.end_col_offset is not None  # TODO
    s = "".join(source_lines[max(loc.lineno - num_lines, 0) : loc.lineno]).rstrip()
    s += "\n" + loc.col_offset * " " + (loc.end_col_offset - loc.col_offset) * "^"
    s = textwrap.dedent(s).splitlines()
    # Add line numbers
    line_numbers = [
        str(line_offset + loc.lineno - i) + ":" for i in range(num_lines, 0, -1)
    ]
    longest = max(len(ln) for ln in line_numbers)
    prefixes = [ln + " " * (longest - len(ln) + indent) for ln in line_numbers]
    res = ""
    for prefix, line in zip(prefixes, s[:-1]):
        res += prefix + line + "\n"
    res += (longest + indent) * " " + s[-1]
    return res


class GuppyModule(object):
    """A Guppy module backed by a Hugr graph.

    Instances of this class can be used as a decorator to add functions to the module.
    After all functions are added, `compile()` must be called to obtain the Hugr.
    """

    name: str
    graph: Hugr
    module_node: Node
    compiler: FunctionCompiler
    # function, AST, source lines, line offset
    annotated_funcs: dict[
        str, tuple[Callable[..., Any], ast.FunctionDef, list[str], int]
    ]
    fun_decls: list[GuppyFunction]

    def __init__(self, name: str):
        self.name = name
        self.graph = Hugr(name)
        self.module_node = self.graph.set_root_name(self.name)
        self.compiler = FunctionCompiler(self.graph)
        self.annotated_funcs = {}
        self.fun_decls = []

    def __call__(self, f: Callable[..., Any]) -> None:
        source_lines, line_offset = inspect.getsourcelines(f)
        line_offset -= 1
        source = "".join(source_lines)  # Lines already have trailing \n's
        source = textwrap.dedent(source)

        func_ast = ast.parse(source).body[0]
        if not isinstance(func_ast, ast.FunctionDef):
            raise GuppyError("Only functions can be placed in modules", func_ast)
        if func_ast.name in self.annotated_funcs:
            raise GuppyError(
                f"Module `{self.name}` already contains a function named `{func_ast.name}` "
                f"(declared at {SourceLoc.from_ast(self.annotated_funcs[func_ast.name][1], line_offset)})",
                func_ast,
            )
        self.annotated_funcs[func_ast.name] = f, func_ast, source_lines, line_offset

    def compile(self, exit_on_error: bool = False) -> Optional[Hugr]:
        """Compiles the module and returns the final Hugr."""
        try:
            global_variables = {}
            defs = {}
            for name, (f, func_ast, _, _) in self.annotated_funcs.items():
                func_ty = self.compiler.validate_signature(func_ast)
                def_node = self.graph.add_def(func_ty, self.module_node, func_ast.name)
                defs[name] = def_node
                global_variables[name] = Variable(
                    name, def_node.out_port(0), {func_ast}
                )
            for name, (
                f,
                func_ast,
                source_lines,
                line_offset,
            ) in self.annotated_funcs.items():
                func = self.compiler.compile(
                    self, func_ast, defs[name], global_variables
                )
                self.fun_decls.append(func)
            return self.graph
        except GuppyError as err:
            if err.location:
                loc = err.location
                line = line_offset + loc.lineno
                print(
                    f"Guppy compilation failed. Error in file {inspect.getsourcefile(f)}:{line}\n",
                    file=sys.stderr,
                )
                print(
                    format_source_location(source_lines, loc, line_offset + 1),
                    file=sys.stderr,
                )
            else:
                print(
                    f'Guppy compilation failed. Error in file "{inspect.getsourcefile(f)}"\n',
                    file=sys.stderr,
                )
            print(
                f"{err.__class__.__name__}: {err.get_msg(line_offset)}", file=sys.stderr
            )
            if exit_on_error:
                sys.exit(1)
            return None


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """Decorator to compile functions outside of modules for testing."""
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=False)
