import ast
import copy
import inspect
import sys
import textwrap

from abc import ABC
from dataclasses import dataclass
from typing import Callable, Union, Optional, Any, Iterator, NamedTuple, Iterable

from guppy.free_names import free_names
from guppy.hugr.hugr import Hugr, Node, DFContainingNode, OutPortV, BlockNode, VNode
from guppy. guppy_types import (IntType, GuppyType, FloatType, BoolType, TypeRow, StringType, type_from_python_value,
                                TupleType, FunctionType)
from guppy.visitor import AstVisitor

AstNode = Union[ast.AST, ast.operator, ast.expr, ast.arg, ast.stmt, ast.Name, ast.keyword, ast.FunctionDef]


@dataclass(frozen=True)
class SourceLoc:
    """ A source location associated with an AST node.

    This class translates the location data provided by the ast module
    into a location inside the file
    """
    line: int
    col: int
    ast_node: Optional[AstNode]

    @staticmethod
    def from_ast(node: AstNode, line_offset: int) -> "SourceLoc":
        return SourceLoc(line_offset + node.lineno, node.col_offset, node)

    def __str__(self) -> str:
        return f"{self.line}:{self.col}"

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, SourceLoc):
            raise NotImplementedError()
        return (self.line, self.col) < (other.line, other.col)


@dataclass
class GuppyError(Exception):
    """ General Guppy error tied to a node in the AST. """
    msg: str
    location: Optional[AstNode] = None


class GuppyTypeError(GuppyError):
    """ Special Guppy exception for type errors. """
    pass


class InternalGuppyError(Exception):
    """ Exception for internal problems during compilation. """
    pass


def assert_arith_type(ty: GuppyType, node: ast.expr) -> None:
    """ Check that a given type is arithmetic, i.e. an integer or float,
    or raise a type error otherwise. """
    if not isinstance(ty, IntType) and not isinstance(ty, FloatType):
        raise GuppyTypeError(f"Expected expression of type `int` or `float`, "
                             f"but got `{ast.unparse(node)}` of type `{ty}`", node)


def assert_int_type(ty: GuppyType, node: ast.expr) -> None:
    """ Check that a given type is integer or raise a type error otherwise. """
    if not isinstance(ty, IntType):
        raise GuppyTypeError(f"Expected expression of type `int`, "
                             f"but got `{ast.unparse(node)}` of type `{ty}`", node)


def assert_bool_type(ty: GuppyType, node: ast.expr) -> None:
    """ Check that a given type is boolean or raise a type error otherwise. """
    if not isinstance(ty, BoolType):
        raise GuppyTypeError(f"Expected expression of type `bool`, "
                             f"but got `{ast.unparse(node)}` of type `{ty}`", node)


class UndefinedPort(OutPortV):
    """ Dummy port for undefined variables.

    Raises an `InternalGuppyError` if one tries to access one of its properties.
    """
    def __init__(self, ty: GuppyType):
        self.ty = ty

    @property
    def node(self) -> Node:  # type: ignore
        raise InternalGuppyError("Tried to access undefined Port")

    @property
    def offset(self) -> int:  # type: ignore
        raise InternalGuppyError("Tried to access undefined Port")


@dataclass(frozen=True)
class Variable:
    """ Class holding all data associated with a variable during compilation.

    Each variable corresponds to a Hugr port. We also store the locations where the
    variable was last defined. Furthermore, variables may collect errors during
    compilation that are only raised if the variable is actually used.
    """
    name: str
    port: OutPortV
    defined_at: set[SourceLoc]  # Set since variable can be defined in `if` and `else` branches

    @property
    def ty(self) -> GuppyType:
        """ The type of the variable. """
        return self.port.ty


def type_from_ast(node: ast.expr) -> GuppyType:
    """ Turns an AST expression into a Guppy type. """
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
    """ Turns an AST expression into a Guppy type row.

    This is needed to interpret the return type annotation of functions.
    """
    # The return type `-> None` is represented in the ast as `ast.Constant(vale=None)`
    if isinstance(node, ast.Constant) and node.value is None:
        return TypeRow([])
    # We turn a tuple return into a row
    elif isinstance(node, ast.Tuple):
        return TypeRow([type_from_ast(el) for el in node.elts])
    # Otherwise, it's a singleton row
    else:
        return TypeRow([type_from_ast(node)])


def is_functional_annotation(stmt: ast.stmt) -> bool:
    """ Returns `True` iff the given statement is the functional pseudo-decorator.

    Pseudo-decorators are built using the matmul operator `@`, i.e. `_@functional`.
    """
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.BinOp):
        op = stmt.value
        if isinstance(op.op, ast.MatMult) and isinstance(op.left, ast.Name) and isinstance(op.right, ast.Name):
            return op.left.id == "_" and op.right.id == "functional"
    return False


# A dictionary mapping names to live variables
VarMap = dict[str, Variable]
ErrMap = dict[str, list[GuppyError]]


@dataclass
class DFContainer:
    """ A dataflow graph under construction.

    This class is passed through the entire compilation pipeline and stores
    the node whose dataflow child-graph is currently being constructed as well
    as all live variables. Note that the variable map is mutated in-place and
    always reflects the current compilation state.
    """
    node: DFContainingNode
    variables: VarMap
    global_variables: VarMap
    errs_on_usage: ErrMap

    def __getitem__(self, item: str) -> Variable:
        return self.variables[item]

    def __setitem__(self, key: str, value: Variable) -> None:
        self.variables[key] = value
        self.errs_on_usage.pop(key, None)

    def __iter__(self) -> Iterator[Variable]:
        return iter(self.variables.values())

    def __contains__(self, item: Union[str, Variable]) -> bool:
        if isinstance(item, str):
            return item in self.variables
        return item in self.variables.values()

    def __copy__(self) -> "DFContainer":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return DFContainer(self.node, self.variables.copy(), self.global_variables, self.errs_on_usage.copy())

    def check_errs_on_usage(self, name_node: ast.Name) -> None:
        if name_node.id in self.errs_on_usage:
            errs = self.errs_on_usage[name_node.id]
            # TODO: Show all errors?
            if len(errs) > 0:
                assert name_node.id not in self.variables
                err = errs[0]
                if err.location is None:
                    err.location = name_node
                raise err


def merge_variables(dfg1: DFContainer, dfg2: DFContainer, port_factory: Callable[[GuppyType], OutPortV] = UndefinedPort) \
        -> tuple[VarMap, ErrMap]:
    """ Merges the variables occurring in two DFGs/BBs.

    Returns a new variable map with the successfully merged variables and an error
    map with the variables that couldn't be merged and should raise an error on
    usage.

    By default, the merged variables will all have undefined ports. Optionally,
    one can pass a `port_factory` that is used to generate ports for the variables
    one by in sorted order.
    """
    merged_vars, errs = {}, {}
    for x in sorted(set(dfg1.variables.keys()) | set(dfg2.variables.keys())):
        if x in dfg1 and x in dfg2:
            v1, v2 = dfg1[x], dfg2[x]
            if v1.ty == v2.ty:
                merged_vars[x] = Variable(x, port_factory(v1.ty), v1.defined_at | v2.defined_at)
            else:
                errs[x] = [GuppyError(f"Variable `{x}` can refer to different types: "
                                      f"`{v1.ty}` (at {', '.join(str(loc) for loc in sorted(v1.defined_at))}) vs "
                                      f"`{v2.ty}` (at {', '.join(str(loc) for loc in sorted(v2.defined_at))})")]
        else:
            # TODO: Tag ast node in DFContainer so we can point to the branch
            errs[x] = [GuppyError(f"Variable `{x}` is not defined on all control-flow paths.")]
    return merged_vars, merge_err_maps(errs, dfg1.errs_on_usage, dfg2.errs_on_usage)


def merge_err_maps(*err_maps: ErrMap) -> ErrMap:
    res: ErrMap = {}
    for d in err_maps:
        for k, v in d.items():
            res.setdefault(k, [])
            res[k] += v
    return res


@dataclass
class BasicBlock(DFContainer):
    """ A basis block under construction.

    The only difference from a regular `DFContainer` is that the node has
    the refined `BlockNode` type.
    """
    node: BlockNode

    def __copy__(self) -> "BasicBlock":
        # Make a copy of the var map so that mutating the copy doesn't
        # mutate our variable mapping
        return BasicBlock(self.node, self.variables.copy(), self.global_variables, self.errs_on_usage.copy())


class CompilerBase(ABC):
    """ Base class for the Guppy compiler.

    Provides utility methods for working with inputs, outputs, DFGs, and blocks.
    """
    graph: Hugr

    def _add_input(self, variables: VarMap, parent: Node) -> VarMap:
        """ Adds an input node with ports for each live variable. """
        # Inputs are ordered lexicographically
        # TODO: Instead we could pass around an explicit variable ordering
        vs = sorted(variables.values(), key=lambda v: v.name)
        inp = self.graph.add_input(output_tys=[v.ty for v in vs], parent=parent)
        return {v.name: Variable(v.name, inp.out_port(i), v.defined_at)
                for (i, v) in enumerate(vs)}

    def _add_output(self, parent: Node, variables: VarMap, extra_outputs: Optional[list[OutPortV]] = None) -> None:
        """ Adds an output node and connects all live variables to it.

        Optionally, some extra ports can be prepended before the variables.
        """
        # Outputs are order lexicographically
        # TODO: Instead we could pass around an explicit variable ordering
        vs = sorted(variables.values(), key=lambda v: v.name)
        extra_outputs = extra_outputs or []
        self.graph.add_output(parent=parent, inputs=extra_outputs + [v.port for v in vs])

    def _begin_new_merge_bb(self, predecessors: list[BasicBlock], merge_vars: VarMap,
                            errs_on_usage: Optional[ErrMap] = None) -> BasicBlock:
        assert len(predecessors) > 0
        block = self.graph.add_block(predecessors[0].node.parent)
        errs_on_usage = merge_err_maps(errs_on_usage or {}, *(p.errs_on_usage for p in predecessors))
        for p in predecessors:
            self.graph.add_edge(p.node.add_out_port(), block.add_in_port())
        new_vars = self._add_input(merge_vars, block)
        return BasicBlock(block, new_vars, predecessors[0].global_variables, errs_on_usage)

    def _begin_new_bb(self, predecessor: BasicBlock) -> BasicBlock:
        """ Creates a basic block, i.e. a `Block` node with an input capturing
        all live variables and connects it to a control flow predecessor BB.
        """
        return self._begin_new_merge_bb([predecessor], predecessor.variables)

    def _finish_bb(self, bb: BasicBlock, subset: Optional[Iterable[str]] = None, branch_pred: Optional[OutPortV] = None,
                   outputs: Optional[list[OutPortV]] = None) -> None:
        """ Finishes a basic block by adding an output node.

        Optionally, only a subset of the active variables in the BB can be
        outputted. Also, if the block branches, an optional port holding the
        branching predicate can be passed.
        Alternatively, a list of ports to output can be passed manually.
        """
        # If the BB doesn't branch, we still need to add a unit () output
        if branch_pred is None:
            unit = self.graph.add_make_tuple([], parent=bb.node).out_port(0)
            branch_pred = self.graph.add_tag(variants=[TupleType([])], tag=0, inp=unit, parent=bb.node).out_port(0)
        if outputs is None:
            variables = {v.name: v for v in bb.variables.values() if subset is None or v.name in subset}
            self._add_output(bb.node, variables, [branch_pred])
        else:
            assert subset is None
            self.graph.add_output(inputs=[branch_pred] + outputs, parent=bb.node)


class ExpressionCompiler(CompilerBase, AstVisitor[OutPortV]):
    """ A compiler from Python expressions to Hugr. """
    dfg: DFContainer

    def __init__(self, graph: Hugr):
        self.graph = graph

    def compile(self, expr: ast.expr, dfg: DFContainer) -> OutPortV:
        """ Compiles an expression and returns a single port holding the output value. """
        self.dfg = dfg
        with self.graph.parent(dfg.node):
            res = self.visit(expr)
        return res

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[OutPortV]:
        """ Compiles a row expression and returns a list of ports, one for
        each value in the row.

        On Python-level, we treat tuples like rows on top-level. However,
        nested tuples are treated like regular Guppy tuples.
        """
        # Top-level tuple is turned into row
        if isinstance(expr, ast.Tuple):
            return [self.compile(e, dfg) for e in expr.elts]
        else:
            return [self.compile(expr, dfg)]

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Any:
        raise GuppyError("Expression not supported", node)

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        if type_from_python_value(node.value) is None:
            raise GuppyError("Unsupported constant expression", node)
        return self.graph.add_constant(node.value).out_port(0)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        self.dfg.check_errs_on_usage(node)
        x = node.id
        if x in self.dfg.variables or x in self.dfg.global_variables:
            var = self.dfg.variables[x] or self.dfg.global_variables[x]
            return var.port
        raise GuppyError(f"Variable `{x}` is not defined", node)

    def visit_JoinedString(self, node: ast.JoinedStr) -> OutPortV:
        raise GuppyError("Guppy does not support formatted strings", node)

    def visit_Tuple(self, node: ast.Tuple) -> OutPortV:
        return self.graph.add_make_tuple(inputs=[self.visit(e) for e in node.elts]).out_port(0)

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
            # The unary invert operator `~` is defined as `~x = -(x + 1)` and only valid for integer
            # types. See https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations
            # TODO: Do we want to follow the Python definition or have a custom HUGR op?
            assert_int_type(ty, node.operand)
            one = self.graph.add_constant(1)
            inc = self.graph.add_arith("iadd", inputs=[port, one.out_port(0)], out_ty=ty)
            inv = self.graph.add_arith("ineg", inputs=[inc.out_port(0)], out_ty=ty)
            return inv.out_port(0)
        else:
            raise InternalGuppyError(f"Unexpected unary operator encountered: {node.op}")

    def binary_arith_op(self, left: OutPortV, left_expr: ast.expr, right: OutPortV, right_expr: ast.expr,
                        int_func: str, float_func: str, bool_out: bool) -> OutPortV:
        """ Helper function for compiling binary arithmetic operations. """
        assert_arith_type(left.ty, left_expr)
        assert_arith_type(right.ty, right_expr)
        # Automatic coercion from `int` to `float` if one of the operands is `float`
        is_float = isinstance(left.ty, FloatType) or isinstance(right.ty, FloatType)
        if is_float:
            if isinstance(left.ty, IntType):
                left = self.graph.add_arith("int_to_float", inputs=[left], out_ty=FloatType()).out_port(0)
            if isinstance(right.ty, IntType):
                right = self.graph.add_arith("int_to_float", inputs=[right], out_ty=IntType()).out_port(0)
        return_ty = BoolType() if bool_out else left.ty  # At this point we have `left.ty == right.ty`
        node = self.graph.add_arith(float_func if is_float else int_func, inputs=[left, right], out_ty=return_ty)
        return node.out_port(0)

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return self.binary_arith_op(left, node.left, right, node.right, "iadd", "fadd", False)
        elif isinstance(node.op, ast.Sub):
            return self.binary_arith_op(left, node.left, right, node.right, "isub", "fsub", False)
        elif isinstance(node.op, ast.Mult):
            return self.binary_arith_op(left, node.left, right, node.right, "imul", "fmul", False)
        elif isinstance(node.op, ast.Div):
            return self.binary_arith_op(left, node.left, right, node.right, "idiv", "fdiv", False)
        elif isinstance(node.op, ast.Mod):
            return self.binary_arith_op(left, node.left, right, node.right, "imod", "fmod", False)
        elif isinstance(node.op, ast.Pow):
            return self.binary_arith_op(left, node.left, right, node.right, "ipow", "fpow", False)
        else:
            raise GuppyError(f"Binary operator `{node.op}` is not supported", node.op)

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
        # Support chained comparisons, e.g. `x <= 5 < y` by compiling to `and(x <= 5, 5 < y)`
        def compile_comparisons() -> Iterator[OutPortV]:
            left_expr = node.left
            left = self.visit(left_expr)
            for right_expr, op in zip(node.comparators, node.ops):
                right = self.visit(right_expr)
                if isinstance(op, ast.Eq) or isinstance(op, ast.Is):
                    # TODO: How is equality defined? What can the operators be?
                    yield self.graph.add_arith("eq", inputs=[left, right], out_ty=BoolType()).out_port(0)
                elif isinstance(op, ast.NotEq) or isinstance(op, ast.IsNot):
                    yield self.graph.add_arith("neq", inputs=[left, right], out_ty=BoolType()).out_port(0)
                elif isinstance(op, ast.Lt):
                    yield self.binary_arith_op(left, left_expr, right, right_expr, "ilt", "flt", True)
                elif isinstance(op, ast.LtE):
                    yield self.binary_arith_op(left, left_expr, right, right_expr, "ileq", "fleq", True)
                elif isinstance(op, ast.Gt):
                    yield self.binary_arith_op(left, left_expr, right, right_expr, "igt", "fgt", True)
                elif isinstance(op, ast.GtE):
                    yield self.binary_arith_op(left, left_expr, right, right_expr, "igeg", "fgeg", True)
                else:
                    # Remaining cases are `in`, and `not in`.
                    # TODO: We want to support this once collections are added
                    raise GuppyError(f"Binary operator `{ast.unparse(op)}` is not supported", op)
                left = right
                left_expr = right_expr

        acc, *rest = list(compile_comparisons())
        for port in rest:
            acc = self.graph.add_arith("and", inputs=[acc, port], out_ty=BoolType()).out_port(0)
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
            acc = self.graph.add_arith(func, inputs=[acc, operand], out_ty=BoolType()).out_port(0)
        return acc

    def visit_Call(self, node: ast.Call) -> OutPortV:
        # We need to figure out if this is a direct or indirect call
        f = node.func
        if isinstance(f, ast.Name) and f.id in self.dfg.global_variables and f.id not in self.dfg.variables:
            is_direct = True
            var = self.dfg.global_variables[f.id]
            func_port = var.port
        else:
            is_direct = False
            func_port = self.visit(f)

        func_ty = func_port.ty
        if not isinstance(func_ty, FunctionType):
            raise GuppyTypeError(f"Expected function type, got `{func_ty}`", f)
        if len(node.keywords) > 0:
            # TODO: Implement this
            raise GuppyError(f"Argument passing by keyword is not supported", node.keywords[0])
        exp, act = len(func_ty.args), len(node.args)
        if exp < act:
            raise GuppyError(f"Not enough arguments passed (expected {exp}, got {act})", node)
        if act < exp:
            raise GuppyError(f"Unexpected argument", node.args[-1])

        args = [self.visit(arg) for arg in node.args]
        for i, port in enumerate(args):
            if port.ty != func_ty.args[i]:
                raise GuppyTypeError(f"Expected argument of type `{func_ty.args[i]}`, got `{port.ty}`", node.args[i])

        if is_direct:
            call = self.graph.add_call(func_port, args)
        else:
            call = self.graph.add_indirect_call(func_port, args)

        # Group outputs into tuple
        returns = [call.out_port(i) for i in range(len(func_ty.returns))]
        if len(returns) > 1:
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        return returns[0]


# Types for control-flow hooks needed for statement compilation
LoopHook = Callable[[BasicBlock], Optional[BasicBlock]]
ReturnHook = Callable[[BasicBlock, ast.Return, list[OutPortV]], Optional[BasicBlock]]


class Hooks(NamedTuple):
    return_hook: ReturnHook
    continue_hook: Optional[LoopHook]
    break_hook: Optional[LoopHook]


class StatementCompiler(CompilerBase, AstVisitor[Optional[BasicBlock]]):
    """ A compiler from Python statements to Hugr. """
    line_offset: int
    expr_compiler: ExpressionCompiler
    functional_stmt_compiler: "FunctionalStatementCompiler"

    def __init__(self, graph: Hugr, line_offset: int):
        self.graph = graph
        self.line_offset = line_offset
        self.expr_compiler = ExpressionCompiler(graph)

    def compile_stms(self, nodes: list[ast.stmt], bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        """ Compiles a list of statements into a basic block given
        a map of all active variables.

        Returns the basic block in which compilation can be resumed afterward.
        Or, returns `None` if all control-flow paths do a jump (i.e. `return`,
        `break` or `continue`.
        """
        bb_opt: Optional[BasicBlock] = bb
        next_functional = False
        for node in nodes:
            if bb_opt is None:
                raise GuppyError("Unreachable code", node)
            if is_functional_annotation(node):
                next_functional = True
                continue

            if next_functional:
                self.functional_stmt_compiler.visit(node, bb_opt, hooks)
                next_functional = False
            else:
                bb_opt = self.visit(node, bb_opt, hooks)
        return bb_opt

    def generic_visit(self, node: Any, *args: Any, **kwargs: Any) -> Optional[BasicBlock]:
        raise GuppyError("Statement not supported", node)

    def visit_Pass(self, node: ast.Pass, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        return bb

    def visit_Assign(self, node: ast.Assign, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        if len(node.targets) > 1:
            # This is the case for assignments like `a = b = 1`
            raise GuppyError("Multi assignment not supported", node)
        target = node.targets[0]
        loc = {SourceLoc.from_ast(node, self.line_offset)}
        row = self.expr_compiler.compile_row(node.value, bb)
        if len(row) == 0:
            # In Python it's fine to assign a void return with the variable
            # being bound to `None` afterward. At the moment, we don't have
            # a `None` type in Guppy, so we raise an error for now.
            # TODO: Think about this. Maybe we should uniformly treat `None`
            #  as the empty tuple?
            raise GuppyError("Cannot unpack empty row")
        assert len(row) > 0

        # Helper function to unpack the row based on the LHS pattern
        def unpack(pattern: AstNode, ports: list[OutPortV]) -> None:
            # Easiest case is if the LHS pattern is a single variable. Note
            # we implicitly pack the row into a tuple if it has more than
            # one element. I.e. `x = 1, 2` works just like `x = (1, 2)`.
            if isinstance(pattern, ast.Name):
                port = ports[0] if len(ports) == 1 else self.graph.add_make_tuple(inputs=ports, parent=bb.node).out_port(0)
                bb[pattern.id] = Variable(pattern.id, port, loc)
            # The only other thing we support right now are tuples
            elif isinstance(pattern, ast.Tuple):
                if len(ports) == 1 and isinstance(ports[0].ty, TupleType):
                    ports = list(self.graph.add_unpack_tuple(input_tuple=ports[0], parent=bb.node).out_ports)
                n, m = len(pattern.elts), len(ports)
                if n != m:
                    raise GuppyTypeError(f"{'Too many' if n < m else 'Not enough'} "
                                         f"values to unpack (expected {n}, got {m})", node)
                for pat, port in zip(pattern.elts, ports):
                    unpack(pat, [port])
            # TODO: Python also supports assignments like `[a, b] = [1, 2]` or
            #  `a, *b = ...`. The former would require some runtime checks but
            #  the latter should be easier to do (unpack and repack the rest).
            else:
                raise GuppyError("Assignment pattern not supported", pattern)

        unpack(target, row)
        return bb

    def visit_AnnAssign(self, node: ast.AnnAssign, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        # TODO: Figure out what to do with type annotations
        raise NotImplementedError()

    def visit_AugAssign(self, node: ast.AugAssign, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        # TODO: Set all source location attributes
        bin_op = ast.BinOp(left=node.target, op=node.op, right=node.value)
        assign = ast.Assign(targets=[node.target], value=bin_op, lineno=node.lineno, col_offset=node.col_offset)
        return self.visit_Assign(assign, bb, hooks)

    def visit_Return(self, node: ast.Return, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        row = self.expr_compiler.compile_row(node.value, bb) if node.value is not None else []
        return hooks.return_hook(bb, node, row)

    def visit_If(self, node: ast.If, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        # Finish the current basic block by putting the if condition at the end
        cond_port = self.expr_compiler.compile(node.test, bb)
        assert_bool_type(cond_port.ty, node.test)
        self._finish_bb(bb, branch_pred=cond_port)

        # Compile statements in the `if` branch
        if_bb = self._begin_new_bb(predecessor=bb)
        if_bb = self.compile_stms(node.body, if_bb, hooks)

        # Compile statements in the `else` branch
        else_exists = len(node.orelse) > 0
        if else_exists:
            # TODO: The logic later would be easier if we always create an else BB, even
            #  if else_exists = False
            else_bb = self._begin_new_bb(predecessor=bb)
            else_bb = self.compile_stms(node.orelse, else_bb, hooks)
        else:  # If we don't have an `else` branch, just use the initial BB
            else_bb = copy.copy(bb)

        # We need to handle different cases depending on whether branches jump (i.e. return, continue, or break)
        if if_bb is None and else_bb is None:
            # Both jump: This means the whole if-statement jumps, so we don't have to do anything
            return None
        elif if_bb is None:
            # If branch jumps: If else branch exists, we can continue in its BB. Otherwise,
            # we have to create a new BB
            if not else_exists:
                else_bb = self._begin_new_bb(predecessor=bb)
            return else_bb
        elif else_bb is None:
            # Else branch jumps: We continue in the BB of the if branch
            return if_bb
        else:
            # No branch jumps: We have to merge the control flow.
            merge_vars, err_vars = merge_variables(if_bb, else_bb)
            self._finish_bb(if_bb, subset=merge_vars.keys())
            self._finish_bb(else_bb, subset=merge_vars.keys())
            return self._begin_new_merge_bb([if_bb, else_bb], merge_vars, err_vars)

    def visit_While(self, node: ast.While, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        # Finish the current basic block
        self._finish_bb(bb)
        # Add basic blocks for loop head, loop body, and loop tail
        head_bb = self._begin_new_bb(predecessor=bb)
        body_bb = self._begin_new_bb(predecessor=head_bb)  # Body must be first successor of head
        tail_bb = self._begin_new_bb(predecessor=head_bb)
        # Insert loop condition into the head
        cond_port = self.expr_compiler.compile(node.test, head_bb)
        assert_bool_type(cond_port.ty, node.test)
        self._finish_bb(head_bb, branch_pred=cond_port)

        free_loop_vars = free_names(node)

        # Define hook that is executed on `continue` and `break`
        def jump_hook(curr_bb: BasicBlock, is_continue: bool) -> Optional[BasicBlock]:
            target_bb = head_bb if is_continue else tail_bb
            self.graph.add_edge(curr_bb.node.add_out_port(), target_bb.node.add_in_port())
            _, errs = merge_variables(bb, curr_bb)

            # TODO: If we reassign a global variable with a different type
            #   in the loop, we run into lots of issues. For example, the
            #   following produces an invalid Hugr since we plug the wrong
            #   type into the output:
            #
            #       x = 42
            #       while True:
            #           x = True

            # Ignore new variables that are only defined in the loop
            self._finish_bb(curr_bb, subset=bb.variables.keys())

            if is_continue:
                # We do another iteration of the loop, so we have to check if
                # any variables occurring freely in the loop condition or body
                # have collected errors during merging
                for x, (err, *_) in errs.items():
                    if x in free_loop_vars:
                        if err.location is None:
                            err.location = free_loop_vars[x]
                        raise err
            tail_bb.errs_on_usage |= errs
            return None

        # Compile loop body
        new_hooks = Hooks(return_hook=hooks.return_hook,
                          continue_hook=lambda curr_bb: jump_hook(curr_bb, True),
                          break_hook=lambda curr_bb: jump_hook(curr_bb, False))
        body_bb_final = self.compile_stms(node.body, body_bb, new_hooks)

        if body_bb_final is None:
            # This happens if the loop body always returns. We continue with tail_bb
            # nonetheless since the loop condition could be false for the first iteration,
            # so it's not a guaranteed return
            return tail_bb

        # Otherwise, jump back to the head.
        jump_hook(body_bb_final, True)

        # Continue compilation in the tail
        return tail_bb

    def visit_Continue(self, node: ast.Continue, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        if not hooks.continue_hook:
            raise InternalGuppyError("Continue hook not defined")
        return hooks.continue_hook(bb)

    def visit_Break(self, node: ast.Break, bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        if not hooks.break_hook:
            raise InternalGuppyError("Break hook not defined")
        return hooks.break_hook(bb)


class FunctionalStatementCompiler(StatementCompiler):
    """ A compiler from Python statements to Hugr only using functional control-flow nodes. """
    def compile_stms(self, nodes: list[ast.stmt], bb: BasicBlock, hooks: Hooks) -> Optional[BasicBlock]:
        self.compile_stmts_functional(nodes, bb, hooks)
        return bb

    def compile_stmts_functional(self, nodes: list[ast.stmt], dfg: DFContainer, hooks: Hooks) -> None:
        """ Compiles a list of statements using only functional control-flow """
        for node in nodes:
            if is_functional_annotation(node):
                raise GuppyError("Statement already contained in a functional block")
            self.visit(node, dfg, hooks)

    def _begin_conditional(self, dfg: DFContainer, cond_port: OutPortV, num_cases: int = 2) \
            -> tuple[VNode, list[DFContainer]]:
        """ Creates a `Conditional` capturing all live variables along with
        a given number of child dataflow `Case` nodes.

        Additionally, returns a new variable map for use inside the `Case`
        dataflow graph.
        """
        cond = self.graph.add_conditional(cond_input=cond_port, inputs=[v.port for v in dfg], parent=dfg.node)
        cases = []
        for _ in range(num_cases):
            case = self.graph.add_case(cond)
            new_vars = self._add_input(dfg.variables, case)
            cases.append(DFContainer(case, new_vars, dfg.global_variables, dfg.errs_on_usage.copy()))
        return cond, cases

    def _begin_tail_loop(self, dfg: DFContainer) -> DFContainer:
        """ Creates a `TailLoop` node with input capturing all live variables. """
        vs = sorted(dfg.variables.values(), key=lambda v: v.name)
        loop = self.graph.add_tail_loop(inputs=[v.port for v in vs], parent=dfg.node)
        new_vars = self._add_input(dfg.variables, loop)
        return DFContainer(loop, new_vars, dfg.global_variables, dfg.errs_on_usage.copy())

    def _finish_dfg(self, dfg: DFContainer, subset: Optional[Iterable[str]] = None) -> None:
        variables = {x: v for x, v in dfg.variables.items() if subset is None or x in subset}
        self._add_output(dfg.node, variables)

    def _finish_tail_loop(self, dfg: DFContainer, cond_port: OutPortV, subset: Optional[Iterable[str]] = None) -> VarMap:
        assert isinstance(dfg.node, VNode)
        variables = {x: v for x, v in dfg.variables.items() if subset is None or x in subset}
        self._add_output(dfg.node, variables, extra_outputs=[cond_port])
        out_vars = {}
        for v in sorted(variables.values(), key=lambda v: v.name):
            out_vars[v.name] = Variable(v.name, dfg.node.add_out_port(v.ty), v.defined_at)
        return out_vars

    def visit_Break(self, node: ast.Break, dfg: DFContainer, hooks: Hooks) -> Optional[BasicBlock]:
        raise GuppyError("Break is not allowed in a functional statement", node)

    def visit_Continue(self, node: ast.Continue, dfg: DFContainer, hooks: Hooks) -> Optional[BasicBlock]:
        raise GuppyError("Continue is not allowed in a functional statement", node)

    def visit_Return(self, node: ast.Return, dfg: DFContainer, hooks: Hooks) -> Optional[BasicBlock]:
        raise GuppyError("Return is not allowed in a functional statement", node)

    def visit_If(self, node: ast.If, dfg: DFContainer, hooks: Hooks) -> Optional[BasicBlock]:
        cond_port = self.expr_compiler.compile(node.test, dfg)
        assert_bool_type(cond_port.ty, node.test)
        conditional, [if_dfg, else_dfg] = self._begin_conditional(dfg, cond_port)
        self.compile_stmts_functional(node.body, if_dfg, hooks)
        self.compile_stmts_functional(node.orelse, else_dfg, hooks)

        merge_vars, errs = merge_variables(if_dfg, else_dfg, port_factory=conditional.add_out_port)
        dfg.errs_on_usage |= errs
        dfg.variables |= merge_vars
        self._finish_dfg(if_dfg, subset=merge_vars.keys())
        self._finish_dfg(else_dfg, subset=merge_vars.keys())
        return None

    def visit_While(self, node: ast.While, dfg: DFContainer, hooks: Hooks) -> Optional[BasicBlock]:
        # Turn into tail-controlled loop using the following transformation:
        #    loop:
        #        if [condition]:
        #            [body]
        #            continue
        #        else:
        #            break

        loop_dfg = self._begin_tail_loop(dfg)
        cond_port = self.expr_compiler.compile(node.test, loop_dfg)
        assert_bool_type(cond_port.ty, node.test)
        conditional, [body_dfg, break_dfg] = self._begin_conditional(loop_dfg, cond_port)
        self.compile_stmts_functional(node.body, body_dfg, hooks)

        self._add_output(body_dfg.node, variables={x: body_dfg[x] for x in dfg.variables},
                         # Return True to continue
                         extra_outputs=[self.graph.add_constant(True, body_dfg.node).out_port(0)])
        self._add_output(break_dfg.node, variables=break_dfg.variables,
                         # Return False to break
                         extra_outputs=[self.graph.add_constant(False, break_dfg.node).out_port(0)])

        # Add output for loop node and update variable map
        assert isinstance(loop_dfg.node, VNode)
        jump_port = conditional.add_out_port(BoolType())
        merge_vars, errs = merge_variables(dfg, body_dfg, port_factory=conditional.add_out_port)
        dfg.variables |= self._finish_tail_loop(loop_dfg, jump_port, subset=merge_vars.keys())
        dfg.errs_on_usage |= errs

        # We have to check that the variables used in the loop head and body haven't
        # collected `errors_on_usage` in the previous iteration.
        for name_node in free_names(node).values():
            dfg.check_errs_on_usage(name_node)
        return None


@dataclass
class GuppyFunction:
    """ Class holding all information associated with a Function during compilation. """
    name: str
    module: "GuppyModule"
    def_node: Node
    ty: FunctionType
    ast: ast.FunctionDef

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # The `@guppy` annotator returns a `GuppyFunction`. If the user
        # tries to call it, we can give a nice error message:
        raise GuppyError("Guppy functions can only be called inside of Guppy functions")


class FunctionCompiler(CompilerBase):
    """ A compiler from Python function definitions to Hugr functions. """
    stmt_compiler: StatementCompiler
    line_offset: int

    def __init__(self, graph: Hugr):
        self.graph = graph
        stmt_compiler = StatementCompiler(graph, 0)
        stmt_compiler.functional_stmt_compiler = FunctionalStatementCompiler(graph, 0)
        stmt_compiler.functional_stmt_compiler.functional_stmt_compiler = stmt_compiler.functional_stmt_compiler
        self.stmt_compiler = stmt_compiler

    @staticmethod
    def validate_signature(func_def: ast.FunctionDef) -> FunctionType:
        """ Checks the signature of a function definition and returns the
        corresponding Guppy type. """
        if len(func_def.args.posonlyargs) != 0:
            raise GuppyError("Positional-only parameters not supported", func_def.args.posonlyargs[0])
        if len(func_def.args.kwonlyargs) != 0:
            raise GuppyError("Keyword-only parameters not supported", func_def.args.kwonlyargs[0])
        if func_def.args.vararg is not None:
            raise GuppyError("*args not supported", func_def.args.vararg)
        if func_def.args.kwarg is not None:
            raise GuppyError("**kwargs not supported", func_def.args.kwarg)
        if func_def.returns is None:
            raise GuppyError("Return type must be annotated", func_def)

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

    def compile(self, module: "GuppyModule", func_def: ast.FunctionDef, def_node: Node, global_variables: VarMap,
                line_offset: int) -> GuppyFunction:
        """ Compiles a `FunctionDef` AST node into a Guppy function. """
        self.line_offset = line_offset
        self.stmt_compiler.line_offset = line_offset

        func_ty = self.validate_signature(func_def)
        args = func_def.args.args

        def_input = self.graph.add_input(parent=def_node)
        cfg = self.graph.add_cfg(def_node, inputs=[def_input.add_out_port(ty) for ty in func_ty.args])
        input_block = self.graph.add_block(cfg)
        input_node = self.graph.add_input(output_tys=func_ty.args, parent=input_block)

        variables: VarMap = {}
        for i, arg in enumerate(args):
            name = arg.arg
            port = input_node.out_port(i)
            variables[name] = Variable(name, port, {SourceLoc.from_ast(arg, self.line_offset)})

        input_bb = BasicBlock(input_block, variables, global_variables, {})
        return_block = self.graph.add_exit(output_tys=func_ty.returns, parent=cfg)

        # Define hook that is executed on return
        def return_hook(curr_bb: BasicBlock, node: ast.Return, row: list[OutPortV]) -> Optional[BasicBlock]:
            tys = [p.ty for p in row]
            if tys != func_ty.returns:
                raise GuppyTypeError(f"Return type mismatch: expected `{TypeRow(func_ty.returns)}`, "
                                     f"got `{TypeRow(tys)}`", node.value)
            self.stmt_compiler._finish_bb(curr_bb, outputs=row)
            self.graph.add_edge(curr_bb.node.add_out_port(), return_block.add_in_port())
            return None

        # Compile function body
        hooks = Hooks(return_hook, None, None)
        final_bb = self.stmt_compiler.compile_stms(func_def.body, input_bb, hooks)

        # If we're still in a basic block after compiling the whole body,
        # we have to add an implicit void return
        if final_bb is not None:
            if len(func_ty.returns) > 0:
                raise GuppyError(f"Expected return statement of type `{TypeRow(func_ty.returns)}`", func_def.body[-1])
            self.stmt_compiler._finish_bb(final_bb, outputs=[])
            self.graph.add_edge(final_bb.node.add_out_port(), return_block.add_in_port())

        # Add final output node for the def block
        self.graph.add_output(inputs=[cfg.add_out_port(ty) for ty in func_ty.returns], parent=def_node)

        return GuppyFunction(func_def.name, module, def_node, func_ty, func_def)


def format_source_location(source_lines: list[str], loc: Union[ast.AST, ast.operator, ast.expr, ast.arg, ast.Name],
                           line_offset: int, num_lines: int = 3, indent: int = 4) -> str:
    """ Creates a pretty banner to show source locations for errors. """
    assert loc.end_col_offset is not None  # TODO
    s = "".join(source_lines[max(loc.lineno-num_lines, 0):loc.lineno]).rstrip()
    s += "\n" + loc.col_offset * " " + (loc.end_col_offset - loc.col_offset) * "^"
    s = textwrap.dedent(s).splitlines()
    # Add line numbers
    line_numbers = [str(line_offset + loc.lineno - i) + ":" for i in range(num_lines, 0, -1)]
    longest = max(len(ln) for ln in line_numbers)
    prefixes = [ln + " " * (longest - len(ln) + indent) for ln in line_numbers]
    res = ""
    for prefix, line in zip(prefixes, s[:-1]):
        res += prefix + line + "\n"
    res += (longest + indent) * " " + s[-1]
    return res


class GuppyModule(object):
    """ A Guppy module backed by a Hugr graph.

    Instances of this class can be used as a decorator to add functions
    to the module. After all functions are added, `compile()` must be
    called to obtain the Hugr.
    """
    name: str
    graph: Hugr
    module_node: Node
    compiler: FunctionCompiler
    # function, AST, source lines, line offset
    annotated_funcs: dict[str, tuple[Callable[..., Any], ast.FunctionDef, list[str], int]]
    fun_decls: list[GuppyFunction]

    def __init__(self, name: str):
        self.name = name
        self.graph = Hugr(name)
        self.module_node = self.graph.add_root(self.name)
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
            raise GuppyError(f"Module `{self.name}` already contains a function named `{func_ast.name}` "
                             f"(declared at {SourceLoc.from_ast(self.annotated_funcs[func_ast.name][1], line_offset)})",
                             func_ast)
        self.annotated_funcs[func_ast.name] = f, func_ast, source_lines, line_offset

    def compile(self, exit_on_error: bool = False) -> Optional[Hugr]:
        """ Compiles the module and returns the final Hugr. """
        try:
            global_variables = {}
            defs = {}
            for name, (f, func_ast, source_lines, line_offset) in self.annotated_funcs.items():
                func_ty = self.compiler.validate_signature(func_ast)
                def_node = self.graph.add_def(func_ty, self.module_node, func_ast.name)
                defs[name] = def_node
                source_loc = SourceLoc.from_ast(func_ast, line_offset)
                global_variables[name] = Variable(name, def_node.out_port(0), {source_loc})
            for name, (f, func_ast, source_lines, line_offset) in self.annotated_funcs.items():
                func = self.compiler.compile(self, func_ast, defs[name], global_variables, line_offset)
                self.fun_decls.append(func)
            return self.graph
        except GuppyError as err:
            if err.location:
                loc = err.location
                line = line_offset + loc.lineno
                print(f"Guppy compilation failed. Error in file {inspect.getsourcefile(f)}:{line}\n", file=sys.stderr)
                print(format_source_location(source_lines, loc, line_offset+1), file=sys.stderr)
            else:
                print(f'Guppy compilation failed. Error in file "{inspect.getsourcefile(f)}"\n', file=sys.stderr)
            print(f"{err.__class__.__name__}: {err.msg}", file=sys.stderr)
            if exit_on_error:
                sys.exit(1)
            return None


def guppy(f: Callable[..., Any]) -> Optional[Hugr]:
    """ Decorator to compile functions outside of modules for testing. """
    module = GuppyModule("module")
    module(f)
    return module.compile(exit_on_error=False)
