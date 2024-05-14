import ast
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, TypeGuard, TypeVar

from hugr.serialization import ops

from guppylang.ast_util import AstVisitor, get_type, with_loc, with_type
from guppylang.cfg.builder import tmp_vars
from guppylang.compiler.core import (
    CompilerBase,
    DFContainer,
    PortVariable,
)
from guppylang.definition.value import CompiledCallableDef, CompiledValueDef
from guppylang.error import GuppyError, InternalGuppyError
from guppylang.hugr_builder.hugr import (
    UNDEFINED,
    DFContainingNode,
    DummyOp,
    OutPortV,
    VNode,
)
from guppylang.nodes import (
    DesugaredGenerator,
    DesugaredListComp,
    GlobalCall,
    GlobalName,
    LocalCall,
    LocalName,
    TensorCall,
    TypeApply,
)
from guppylang.tys.builtin import bool_type, get_element_type, is_list_type
from guppylang.tys.subst import Inst
from guppylang.tys.ty import (
    BoundTypeVar,
    FunctionType,
    NoneType,
    TupleType,
    Type,
    type_to_row,
)


class ExprCompiler(CompilerBase, AstVisitor[OutPortV]):
    """A compiler from guppylang expressions to Hugr."""

    dfg: DFContainer

    def compile(self, expr: ast.expr, dfg: DFContainer) -> OutPortV:
        """Compiles an expression and returns a single port holding the output value."""
        self.dfg = dfg
        with self.graph.parent(dfg.node):
            res = self.visit(expr)
        return res

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[OutPortV]:
        """Compiles a row expression and returns a list of ports, one for each value in
        the row.

        On Python-level, we treat tuples like rows on top-level. However, nested tuples
        are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    @contextmanager
    def _new_dfcontainer(
        self, inputs: list[ast.Name], node: DFContainingNode
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `DFContainer`.

        Automatically updates `self.dfg` and makes the inputs available.
        """
        old = self.dfg
        inp = self.graph.add_input(parent=node)
        # Check that the input names are unique
        assert len({inp.id for inp in inputs}) == len(inputs), "Inputs are not unique"
        new_locals = {
            name.id: PortVariable(name.id, inp.add_out_port(get_type(name)), name, None)
            for name in inputs
        }
        self.dfg = DFContainer(node, self.dfg.locals | new_locals)
        with self.graph.parent(node):
            yield
        self.dfg = old

    @contextmanager
    def _new_loop(
        self,
        loop_vars: list[ast.Name],
        branch: ast.Name,
        parent: DFContainingNode | None = None,
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `TailLoop` node.

        Automatically adds the `Output` node to the loop body once the context manager
        exits.
        """
        loop = self.graph.add_tail_loop(
            [self.visit(name) for name in loop_vars], parent
        )
        with self._new_dfcontainer(loop_vars, loop):
            yield
            # Output the branch predicate and the inputs for the next iteration
            self.graph.add_output(
                # Note that we have to do fresh calls to `self.visit` here since we're
                # in a new context
                [self.visit(branch), *(self.visit(name) for name in loop_vars)]
            )
        # Update the DFG with the outputs from the loop
        for name in loop_vars:
            self.dfg[name.id].port = loop.add_out_port(get_type(name))

    @contextmanager
    def _new_case(
        self, inputs: list[ast.Name], outputs: list[ast.Name], cond_node: VNode
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `Case` node.

        Automatically adds the `Output` node once the context manager exits.
        """
        with self._new_dfcontainer(inputs, self.graph.add_case(cond_node)):
            yield
            self.graph.add_output([self.visit(name) for name in outputs])

    @contextmanager
    def _if_true(self, cond: ast.expr, inputs: list[ast.Name]) -> Iterator[None]:
        """Context manager to build a graph inside the `true` case of a `Conditional`

        In the `false` case, the inputs are outputted as is.
        """
        cond_node = self.graph.add_conditional(
            self.visit(cond), [self.visit(inp) for inp in inputs]
        )
        # If the condition is false, output the inputs as is
        with self._new_case(inputs, inputs, cond_node):
            pass
        # If the condition is true, we enter the `with` block
        with self._new_case(inputs, inputs, cond_node):
            yield
        # Update the DFG with the outputs from the Conditional node
        for name in inputs:
            self.dfg[name.id].port = cond_node.add_out_port(get_type(name))

    def visit_Constant(self, node: ast.Constant) -> OutPortV:
        if value := python_value_to_hugr(node.value, get_type(node)):
            const = self.graph.add_constant(value, get_type(node)).out_port(0)
            return self.graph.add_load_constant(const).out_port(0)
        raise InternalGuppyError("Unsupported constant expression in compiler")

    def visit_LocalName(self, node: LocalName) -> OutPortV:
        return self.dfg[node.id].port

    def visit_GlobalName(self, node: GlobalName) -> OutPortV:
        defn = self.globals[node.def_id]
        assert isinstance(defn, CompiledValueDef)
        if isinstance(defn, CompiledCallableDef) and defn.ty.parametrized:
            raise GuppyError(
                "Usage of polymorphic functions as dynamic higher-order values is not "
                "supported yet",
                node,
            )
        return defn.load(self.dfg, self.graph, self.globals, node)

    def visit_Name(self, node: ast.Name) -> OutPortV:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Tuple(self, node: ast.Tuple) -> OutPortV:
        return self.graph.add_make_tuple(
            inputs=[self.visit(e) for e in node.elts]
        ).out_port(0)

    def visit_List(self, node: ast.List) -> OutPortV:
        # Note that this is a list literal (i.e. `[e1, e2, ...]`), not a comprehension
        return self.graph.add_node(
            DummyOp("MakeList"), inputs=[self.visit(e) for e in node.elts]
        ).add_out_port(get_type(node))

    def _unpack_tuple(self, wire: OutPortV) -> list[OutPortV]:
        unpack_node = self.graph.add_unpack_tuple(wire, self.dfg.node)
        return list(unpack_node.out_ports)

    def _pack_returns(self, returns: list[OutPortV], return_ty: Type) -> OutPortV:
        """Groups function return values into a tuple"""
        if isinstance(return_ty, TupleType | NoneType) and not return_ty.preserve:
            assert len(returns) == (
                len(return_ty.element_types) if isinstance(return_ty, TupleType) else 0
            )
            return self.graph.add_make_tuple(inputs=returns).out_port(0)
        assert len(returns) == 1
        return returns[0]

    def visit_LocalCall(self, node: LocalCall) -> OutPortV:
        func = self.visit(node.func)
        assert isinstance(func.ty, FunctionType)

        args = [self.visit(arg) for arg in node.args]
        call = self.graph.add_indirect_call(func, args)
        rets = [call.out_port(i) for i in range(len(type_to_row(func.ty.output)))]
        return self._pack_returns(rets, func.ty.output)

    def visit_TensorCall(self, node: TensorCall) -> OutPortV:
        func = self.visit(node.func)
        args = [self.visit(arg) for arg in node.args]

        assert isinstance(func.ty, TupleType)

        rets: list[OutPortV] = []
        remaining_args = args
        for elem in self._unpack_tuple(func):
            outs, remaining_args = self._compile_tensor_with_leftovers(
                elem, remaining_args
            )
            rets.extend(outs)
        assert remaining_args == []

        return self._pack_returns(rets, node.out_tys)

    def _compile_tensor_with_leftovers(
        self, func: OutPortV, args: list[OutPortV]
    ) -> tuple[
        list[OutPortV],  # Compiled outputs
        list[OutPortV],
    ]:  # Leftover args
        if isinstance(func.ty, TupleType):
            remaining_args = args
            all_outs = []
            for elem in self._unpack_tuple(func):
                outs, remaining_args = self._compile_tensor_with_leftovers(
                    elem, remaining_args
                )
                all_outs.extend(outs)
            return all_outs, remaining_args

        elif isinstance(func.ty, FunctionType):
            input_len = len(func.ty.inputs)
            call = self.graph.add_indirect_call(func, args[0:input_len])

            return list(call.out_ports), args[input_len:]
        else:
            raise InternalGuppyError("Tensor element wasn't function or tuple")

    def visit_GlobalCall(self, node: GlobalCall) -> OutPortV:
        func = self.globals[node.def_id]
        assert isinstance(func, CompiledCallableDef)

        args = [self.visit(arg) for arg in node.args]
        rets = func.compile_call(
            args, list(node.type_args), self.dfg, self.graph, self.globals, node
        )
        return self._pack_returns(rets, func.ty.output)

    def visit_Call(self, node: ast.Call) -> OutPortV:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_TypeApply(self, node: TypeApply) -> OutPortV:
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

        return defn.load_with_args(node.inst, self.dfg, self.graph, self.globals, node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> OutPortV:
        # The only case that is not desugared by the type checker is the `not` operation
        # since it is not implemented via a dunder method
        if isinstance(node.op, ast.Not):
            arg = self.visit(node.operand)
            op = ops.CustomOp(
                extension="logic", op_name="Not", args=[], parent=UNDEFINED
            )
            return self.graph.add_node(ops.OpType(op), inputs=[arg]).add_out_port(
                bool_type()
            )

        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> OutPortV:
        from guppylang.compiler.stmt_compiler import StmtCompiler

        compiler = StmtCompiler(self.graph, self.globals)

        # Make up a name for the list under construction and bind it to an empty list
        list_ty = get_type(node)
        list_name = with_type(list_ty, with_loc(node, LocalName(id=next(tmp_vars))))
        empty_list = self.graph.add_node(DummyOp("MakeList"))
        self.dfg[list_name.id] = PortVariable(
            list_name.id, empty_list.add_out_port(list_ty), node, None
        )

        def compile_generators(elt: ast.expr, gens: list[DesugaredGenerator]) -> None:
            """Helper function to generate nested TailLoop nodes for generators"""
            # If there are no more generators left, just append the element to the list
            if not gens:
                list_port, elt_port = self.visit(list_name), self.visit(elt)
                push = self.graph.add_node(
                    DummyOp("Push"), inputs=[list_port, elt_port]
                )
                self.dfg[list_name.id].port = push.add_out_port(list_port.ty)
                return

            # Otherwise, compile the first iterator and construct a TailLoop
            gen, *gens = gens
            compiler.compile_stmts([gen.iter_assign], self.dfg)
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

    def visit_BinOp(self, node: ast.BinOp) -> OutPortV:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Compare(self, node: ast.Compare) -> OutPortV:
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


def python_value_to_hugr(v: Any, exp_ty: Type) -> ops.Value | None:
    """Turns a Python value into a Hugr value.

    Returns None if the Python value cannot be represented in Guppy.
    """
    from guppylang.prelude._internal import (
        bool_value,
        float_value,
        int_value,
        list_value,
    )

    match v:
        case bool():
            return bool_value(v)
        case int():
            return int_value(v)
        case float():
            return float_value(v)
        case tuple(elts):
            assert isinstance(exp_ty, TupleType)
            vs = [
                python_value_to_hugr(elt, ty)
                for elt, ty in zip(elts, exp_ty.element_types)
            ]
            if doesnt_contain_none(vs):
                return ops.Value(ops.TupleValue(vs=vs))
        case list(elts):
            assert is_list_type(exp_ty)
            vs = [python_value_to_hugr(elt, get_element_type(exp_ty)) for elt in elts]
            if doesnt_contain_none(vs):
                return list_value(vs, get_element_type(exp_ty))
        case _:
            # Pytket conversion is an optional feature
            try:
                import pytket

                if isinstance(v, pytket.circuit.Circuit):
                    from tket2.circuit import (  # type: ignore[import-untyped, import-not-found, unused-ignore]
                        Tk2Circuit,
                    )

                    hugr = json.loads(Tk2Circuit(v).to_hugr_json())
                    return ops.Value(ops.FunctionValue(hugr=hugr))
            except ImportError:
                pass
    return None


T = TypeVar("T")


def doesnt_contain_none(xs: list[T | None]) -> TypeGuard[list[T]]:
    """Checks if a list contains `None`."""
    return all(x is not None for x in xs)
