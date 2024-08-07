import ast
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any, TypeGuard, TypeVar, cast

import hugr
from hugr import Node, Wire, ops
from hugr import tys as ht
from hugr import val as hv
from hugr.cond_loop import Conditional
from hugr.dfg import _DfBase

from guppylang.ast_util import AstVisitor, get_type, with_loc, with_type
from guppylang.cfg.builder import tmp_vars
from guppylang.checker.core import Variable
from guppylang.compiler.core import CompilerBase, DFContainer
from guppylang.definition.value import CompiledCallableDef, CompiledValueDef
from guppylang.error import GuppyError, InternalGuppyError
from guppylang.nodes import (
    DesugaredGenerator,
    DesugaredListComp,
    FieldAccessAndDrop,
    GlobalCall,
    GlobalName,
    LocalCall,
    PlaceNode,
    ResultExpr,
    TensorCall,
    TypeApply,
)
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import get_element_type, is_list_type
from guppylang.tys.const import ConstValue
from guppylang.tys.subst import Inst
from guppylang.tys.ty import (
    BoundTypeVar,
    FunctionType,
    NoneType,
    NumericType,
    TupleType,
    Type,
)

DP = TypeVar("DP", bound=ops.DfParentOp)


class ExprCompiler(CompilerBase, AstVisitor[Wire]):
    """A compiler from guppylang expressions to Hugr."""

    dfg: DFContainer

    def compile(self, expr: ast.expr, dfg: DFContainer) -> Wire:
        """Compiles an expression and returns a single port holding the output value."""
        self.dfg = dfg
        return self.visit(expr)

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[Wire]:
        """Compiles a row expression and returns a list of ports, one for each value in
        the row.

        On Python-level, we treat tuples like rows on top-level. However, nested tuples
        are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    @property
    def builder(self) -> _DfBase[ops.DfParentOp]:
        """The current Hugr dataflow graph builder."""
        return self.dfg.builder

    @contextmanager
    def _new_dfcontainer(
        self, inputs: list[PlaceNode], builder: _DfBase[DP]
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `DFContainer`.

        Automatically updates `self.dfg` and makes the inputs available.
        """
        old = self.dfg
        # Check that the input names are unique
        assert len({inp.place.id for inp in inputs}) == len(
            inputs
        ), "Inputs are not unique"
        self.dfg = DFContainer(builder, self.dfg.locals.copy())
        hugr_input: Node = builder.input_node
        for input_node, wire in zip(inputs, hugr_input[:], strict=True):
            self.dfg[input_node.place] = wire

        yield

        self.dfg = old

    @contextmanager
    def _new_loop(
        self,
        loop_vars: list[PlaceNode],
        branch: PlaceNode,
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `TailLoop` node.

        Automatically adds the `Output` node to the loop body once the context manager
        exits.
        """
        loop_inputs = [self.visit(name) for name in loop_vars]
        loop = self.builder.add_tail_loop([], loop_inputs)
        with self._new_dfcontainer(loop_vars, loop):
            yield
            # Output the branch predicate and the inputs for the next iteration
            loop.set_loop_outputs(
                # Note that we have to do fresh calls to `self.visit` here since we're
                # in a new context
                self.visit(branch),
                *(self.visit(name) for name in loop_vars),
            )
        # Update the DFG with the outputs from the loop
        for node, wire in zip(loop_vars, loop.parent_node[:], strict=True):
            self.dfg[node.place] = wire

    @contextmanager
    def _new_case(
        self,
        inputs: list[PlaceNode],
        outputs: list[PlaceNode],
        conditional: Conditional,
        case_id: int,
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `Case` node.

        Automatically adds the `Output` node once the context manager exits.
        """
        # TODO: `Case` is `_DfgBase`, but not `Dfg`?
        case = conditional.add_case(case_id)
        with self._new_dfcontainer(inputs, case):
            yield
            case.set_outputs(*(self.visit(name) for name in outputs))

    @contextmanager
    def _if_true(self, cond: ast.expr, inputs: list[PlaceNode]) -> Iterator[None]:
        """Context manager to build a graph inside the `true` case of a `Conditional`

        In the `false` case, the inputs are outputted as is.
        """
        conditional = self.builder.add_conditional(
            self.visit(cond), *(self.visit(inp) for inp in inputs)
        )
        with self._new_case(inputs, inputs, conditional, 0):
            yield
        # If the condition is false, output the inputs as is
        with self._new_case(inputs, inputs, conditional, 1):
            pass
        # Update the DFG with the outputs from the Conditional node
        for node, wire in zip(inputs, conditional.parent_node[:], strict=True):
            self.dfg[node.place] = wire

    def visit_Constant(self, node: ast.Constant) -> Wire:
        if value := python_value_to_hugr(node.value, get_type(node)):
            return self.builder.load(value)
        raise InternalGuppyError("Unsupported constant expression in compiler")

    def visit_PlaceNode(self, node: PlaceNode) -> Wire:
        return self.dfg[node.place]

    def visit_GlobalName(self, node: GlobalName) -> Wire:
        defn = self.globals[node.def_id]
        assert isinstance(defn, CompiledValueDef)
        if isinstance(defn, CompiledCallableDef) and defn.ty.parametrized:
            raise GuppyError(
                "Usage of polymorphic functions as dynamic higher-order values is not "
                "supported yet",
                node,
            )
        return defn.load(self.dfg, self.globals, node)

    def visit_Name(self, node: ast.Name) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Tuple(self, node: ast.Tuple) -> Wire:
        elems = [self.visit(e) for e in node.elts]
        types = [get_type(e) for e in node.elts]
        return self._pack_tuple(elems, types)

    def visit_List(self, node: ast.List) -> Wire:
        # Note that this is a list literal (i.e. `[e1, e2, ...]`), not a comprehension
        inputs = [self.visit(e) for e in node.elts]
        in_types = [get_type(e) for e in node.elts]
        out_type = get_type(node)
        return self.builder.add_op(
            make_list_op(in_types, out_type),
            *inputs,
        )

    def _unpack_tuple(self, wire: Wire, types: Sequence[Type]) -> Sequence[Wire]:
        """Add a tuple unpack operation to the graph"""
        types = [t.to_hugr() for t in types]
        return list(self.builder.add_op(ops.UnpackTuple(types), wire))

    def _pack_tuple(self, wires: Sequence[Wire], types: Sequence[Type]) -> Wire:
        """Add a tuple pack operation to the graph"""
        types = [t.to_hugr() for t in types]
        return self.builder.add_op(ops.MakeTuple(types), *wires)

    def _pack_returns(self, returns: Sequence[Wire], return_ty: Type) -> Wire:
        """Groups function return values into a tuple"""
        if isinstance(return_ty, TupleType | NoneType) and not return_ty.preserve:
            types = return_ty.element_types if isinstance(return_ty, TupleType) else []
            assert len(returns) == len(types)
            return self._pack_tuple(returns, types)
        assert len(returns) == 1
        return returns[0]

    def visit_LocalCall(self, node: LocalCall) -> Wire:
        func = self.visit(node.func)
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)

        func_hugr_ty = func_ty.to_hugr_poly().body
        assert isinstance(func_hugr_ty, ht.FunctionType)

        args = [self.visit(arg) for arg in node.args]
        call = self.builder.add_op(ops.CallIndirect(func_hugr_ty), func, *args)
        return self._pack_returns(list(call), func_ty.output)

    def visit_TensorCall(self, node: TensorCall) -> Wire:
        functions: Wire = self.visit(node.func)
        function_types = get_type(node.func)

        args = [self.visit(arg) for arg in node.args]
        assert isinstance(function_types, TupleType)

        rets: list[Wire] = []
        remaining_args = args
        for func, func_ty in zip(
            self._unpack_tuple(functions, function_types.element_types),
            function_types.element_types,
            strict=True,
        ):
            outs, remaining_args = self._compile_tensor_with_leftovers(
                func, func_ty, remaining_args
            )
            rets.extend(outs)
        assert (
            remaining_args == []
        ), "Not all function arguments were consumed after a tensor call"

        return self._pack_returns(rets, node.out_tys)

    def _compile_tensor_with_leftovers(
        self, func: Wire, func_ty: Type, args: list[Wire]
    ) -> tuple[
        list[Wire],  # Compiled outputs
        list[Wire],  # Leftover args
    ]:
        """Compiles a function call, consuming as many arguments as needed, and
        returning the unused ones.
        """
        if isinstance(func_ty, TupleType):
            remaining_args = args
            all_outs = []
            for elem, ty in zip(
                self._unpack_tuple(func, func_ty.element_types),
                func_ty.element_types,
                strict=True,
            ):
                outs, remaining_args = self._compile_tensor_with_leftovers(
                    elem, ty, remaining_args
                )
                all_outs.extend(outs)
            return all_outs, remaining_args

        elif isinstance(func_ty, FunctionType):
            hugr_ty = func_ty.to_hugr()
            assert isinstance(hugr_ty, ht.FunctionType)

            func_hugr_ty = func_ty.to_hugr_poly().body
            assert isinstance(func_hugr_ty, ht.FunctionType)

            input_len = len(func_ty.inputs)
            call = self.builder.add_op(
                ops.CallIndirect(func_hugr_ty), func, *args[0:input_len]
            )

            return list(call), args[input_len:]
        else:
            raise InternalGuppyError("Tensor element wasn't function or tuple")

    def visit_GlobalCall(self, node: GlobalCall) -> Wire:
        func = self.globals[node.def_id]
        assert isinstance(func, CompiledCallableDef)

        args = [self.visit(arg) for arg in node.args]
        rets = func.compile_call(
            args, list(node.type_args), self.dfg, self.globals, node
        )
        return self._pack_returns(rets, func.ty.output)

    def visit_Call(self, node: ast.Call) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_TypeApply(self, node: TypeApply) -> Wire:
        # For now, we can only TypeApply global FunctionDefs/Decls.
        if not isinstance(node.value, GlobalName):
            raise InternalGuppyError("Dynamic TypeApply not supported yet!")
        defn = self.globals[node.value.def_id]
        assert isinstance(defn, CompiledCallableDef)

        # We have to be very careful here: If we instantiate `foo: forall T. T -> T`
        # with a tuple type `tuple[A, B]`, we get the type `tuple[A, B] -> tuple[A, B]`.
        # Normally, this would be represented in Hugr as a function with two output
        # ports types A and B. However, when TypeApplying `foo`, we actually get a
        # function with a single output port typed `tuple[A, B]`.
        # TODO: We would need to do manual monomorphisation in that case to obtain a
        #  function that returns two ports as expected
        if instantiation_needs_unpacking(defn.ty, node.inst):
            raise GuppyError(
                "Generic function instantiations returning rows are not supported yet",
                node,
            )

        return defn.load_with_args(node.inst, self.dfg, self.globals, node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Wire:
        # The only case that is not desugared by the type checker is the `not` operation
        # since it is not implemented via a dunder method
        if isinstance(node.op, ast.Not):
            from guppylang.prelude._internal.util import logic_op

            arg = self.visit(node.operand)
            return self.builder.add_op(logic_op("Not", args=[], inputs=1), arg)

        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_FieldAccessAndDrop(self, node: FieldAccessAndDrop) -> Wire:
        struct_port = self.visit(node.value)
        return self._unpack_tuple(struct_port, [f.ty for f in node.struct_ty.fields])[0]

    def visit_ResultExpr(self, node: ResultExpr) -> Wire:
        type_args = [
            TypeArg(node.ty),
            ConstArg(ConstValue(value=node.tag, ty=NumericType(NumericType.Kind.Nat))),
        ]
        sig = ht.FunctionType(
            input=[node.ty.to_hugr()],
            output=[],
        )
        op = ops.Custom(
            extension="tket2.results",
            name="Result",
            args=[arg.to_hugr() for arg in type_args],
            signature=sig,
        )
        self.builder.add_op(op, self.visit(node.value))
        return self._pack_returns([], NoneType())

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> Wire:
        from guppylang.compiler.stmt_compiler import StmtCompiler

        compiler = StmtCompiler(self.globals)

        # Make up a name for the list under construction and bind it to an empty list
        list_ty = get_type(node)
        list_place = Variable(next(tmp_vars), list_ty, node)
        list_name = with_type(list_ty, with_loc(node, PlaceNode(place=list_place)))
        self.dfg[list_place] = self.builder.add_op(make_list_op([], list_ty))

        def compile_generators(elt: ast.expr, gens: list[DesugaredGenerator]) -> None:
            """Helper function to generate nested TailLoop nodes for generators"""
            # If there are no more generators left, just append the element to the list
            if not gens:
                list_port, elt_port = self.visit(list_name), self.visit(elt)
                elt_ty = get_type(elt)
                push = self.builder.add_op(
                    list_push_op(list_ty, elt_ty), list_port, elt_port
                )
                self.dfg[list_place] = push
                return

            # Otherwise, compile the first iterator and construct a TailLoop
            gen, *gens = gens
            compiler.compile_stmts([gen.iter_assign], self.dfg)
            assert isinstance(gen.iter, PlaceNode)
            assert isinstance(gen.hasnext, PlaceNode)
            inputs = [gen.iter, list_name]
            with self._new_loop(inputs, gen.hasnext):
                # If there is a next element, compile it and continue with the next
                # generator
                compiler.compile_stmts([gen.hasnext_assign], self.dfg)
                with self._if_true(gen.hasnext, inputs):

                    def compile_ifs(ifs: list[ast.expr]) -> None:
                        """Helper function to compile a series of if-guards into nested
                        Conditional nodes."""
                        if ifs:
                            if_expr, *ifs = ifs
                            # If the condition is true, continue with the next one
                            with self._if_true(if_expr, inputs):
                                compile_ifs(ifs)
                        else:
                            # If there are no guards left, compile the next generator
                            compile_generators(elt, gens)

                    compiler.compile_stmts([gen.next_assign], self.dfg)
                    compile_ifs(gen.ifs)

            # After the loop is done, we have to finalize the iterator
            self.visit(gen.iterend)

        compile_generators(node.elt, node.generators)
        return self.visit(list_name)

    def visit_BinOp(self, node: ast.BinOp) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Compare(self, node: ast.Compare) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")


def expr_to_row(expr: ast.expr) -> list[ast.expr]:
    """Turns an expression into a row expressions by unpacking top-level tuples."""
    return expr.elts if isinstance(expr, ast.Tuple) else [expr]


def instantiation_needs_unpacking(func_ty: FunctionType, inst: Inst) -> bool:
    """Checks if instantiating a polymorphic makes it return a row."""
    if isinstance(func_ty.output, BoundTypeVar):
        return_ty = inst[func_ty.output.idx]
        return isinstance(return_ty, TupleType | NoneType)
    return False


def python_value_to_hugr(v: Any, exp_ty: Type) -> hv.Value | None:
    """Turns a Python value into a Hugr value.

    Returns None if the Python value cannot be represented in Guppy.
    """
    from guppylang.prelude._internal.util import ListVal

    match v:
        case bool():
            return hv.bool_value(v)
        case int():
            return hugr.std.int.IntVal(v)
        case float():
            return hugr.std.float.FloatVal(v)
        case tuple(elts):
            assert isinstance(exp_ty, TupleType)
            vs = [
                python_value_to_hugr(elt, ty)
                for elt, ty in zip(elts, exp_ty.element_types, strict=True)
            ]
            if doesnt_contain_none(vs):
                return hv.Tuple(*vs)
        case list(elts):
            assert is_list_type(exp_ty)
            vs = [python_value_to_hugr(elt, get_element_type(exp_ty)) for elt in elts]
            if doesnt_contain_none(vs):
                return ListVal(vs, get_element_type(exp_ty))
        case _:
            # Pytket conversion is an optional feature
            try:
                import pytket

                if isinstance(v, pytket.circuit.Circuit):
                    from tket2.circuit import (  # type: ignore[import-untyped, import-not-found, unused-ignore]
                        Tk2Circuit,
                    )

                    circ = json.loads(Tk2Circuit(v).to_hugr_json())  # type: ignore[attr-defined, unused-ignore]
                    return hv.Function(circ)
            except ImportError:
                pass
    return None


def make_dummy_op(
    name: str, inp: Sequence[Type], out: Sequence[Type]
) -> ops.DataflowOp:
    """Dummy operation."""
    input = [ty.to_hugr() for ty in inp]
    output = [ty.to_hugr() for ty in out]

    sig = ht.FunctionType(input=input, output=output)
    return ops.Custom(name=name, extension="dummy", signature=sig, args=[])


def make_list_op(in_types: Sequence[Type], out_type: Type) -> ops.DataflowOp:
    """Creates a dummy operation for constructing a list."""
    return make_dummy_op("MakeList", in_types, [out_type])


def list_push_op(list_ty: Type, elem_ty: Type) -> ops.DataflowOp:
    """Creates a dummy operation for constructing a list."""
    return make_dummy_op("Push", [list_ty, elem_ty], [list_ty])


T = TypeVar("T")


def doesnt_contain_none(xs: list[T | None]) -> TypeGuard[list[T]]:
    """Checks if a list contains `None`."""
    return all(x is not None for x in xs)
