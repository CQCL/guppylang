import ast
from collections.abc import Iterable, Iterator, Sequence
from contextlib import AbstractContextManager, ExitStack, contextmanager
from typing import Any, Final, TypeGuard, TypeVar

import hugr
import hugr.std.collections.array
import hugr.std.float
import hugr.std.int
import hugr.std.logic
import hugr.std.prelude
from hugr import Wire, ops
from hugr import tys as ht
from hugr import val as hv
from hugr.build import function as hf
from hugr.build.cond_loop import Conditional
from hugr.build.dfg import DP, DfBase
from typing_extensions import assert_never

from guppylang.ast_util import AstNode, AstVisitor, get_type
from guppylang.cfg.builder import tmp_vars
from guppylang.checker.core import Variable, contains_subscript
from guppylang.checker.errors.generic import UnsupportedError
from guppylang.compiler.core import (
    CompilerBase,
    CompilerContext,
    DFContainer,
    GlobalConstId,
)
from guppylang.compiler.hugr_extension import PartialOp
from guppylang.definition.custom import CustomFunctionDef
from guppylang.definition.value import (
    CallReturnWires,
    CompiledCallableDef,
    CompiledValueDef,
)
from guppylang.error import GuppyError, InternalGuppyError
from guppylang.nodes import (
    BarrierExpr,
    DesugaredArrayComp,
    DesugaredGenerator,
    DesugaredListComp,
    ExitKind,
    FieldAccessAndDrop,
    GenericParamValue,
    GlobalCall,
    GlobalName,
    LocalCall,
    PanicExpr,
    PartialApply,
    PlaceNode,
    ResultExpr,
    SubscriptAccessAndDrop,
    TensorCall,
    TypeApply,
)
from guppylang.std._internal.compiler.arithmetic import convert_ifromusize
from guppylang.std._internal.compiler.array import array_map, array_repeat
from guppylang.std._internal.compiler.list import (
    list_new,
)
from guppylang.std._internal.compiler.prelude import (
    build_error,
    build_panic,
    build_unwrap,
    panic,
)
from guppylang.tys.arg import Argument
from guppylang.tys.builtin import (
    bool_type,
    get_element_type,
    int_type,
    is_bool_type,
    is_frozenarray_type,
)
from guppylang.tys.subst import Inst
from guppylang.tys.ty import (
    BoundTypeVar,
    FuncInput,
    FunctionType,
    InputFlags,
    NoneType,
    NumericType,
    OpaqueType,
    TupleType,
    Type,
    type_to_row,
)


class ExprCompiler(CompilerBase, AstVisitor[Wire]):
    """A compiler from guppylang expressions to Hugr."""

    dfg: DFContainer

    def compile(self, expr: ast.expr, dfg: DFContainer) -> Wire:
        """Compiles an expression and returns a single wire holding the output value."""
        self.dfg = dfg
        return self.visit(expr)

    def compile_row(self, expr: ast.expr, dfg: DFContainer) -> list[Wire]:
        """Compiles a row expression and returns a list of wires, one for each value in
        the row.

        On Python-level, we treat tuples like rows on top-level. However, nested tuples
        are treated like regular Guppy tuples.
        """
        return [self.compile(e, dfg) for e in expr_to_row(expr)]

    @property
    def builder(self) -> DfBase[ops.DfParentOp]:
        """The current Hugr dataflow graph builder."""
        return self.dfg.builder

    @contextmanager
    def _new_dfcontainer(
        self, inputs: list[PlaceNode], builder: DfBase[DP]
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
        hugr_input = builder.input_node
        for input_node, wire in zip(inputs, hugr_input, strict=True):
            self.dfg[input_node.place] = wire

        yield

        self.dfg = old

    @contextmanager
    def _new_loop(
        self,
        just_inputs_vars: list[PlaceNode],
        loop_vars: list[PlaceNode],
        break_predicate: PlaceNode,
    ) -> Iterator[None]:
        """Context manager to build a graph inside a new `TailLoop` node.

        Automatically adds the `Output` node to the loop body once the context manager
        exits.
        """
        just_inputs = [self.visit(name) for name in just_inputs_vars]
        loop_inputs = [self.visit(name) for name in loop_vars]
        loop = self.builder.add_tail_loop(just_inputs, loop_inputs)
        with self._new_dfcontainer(just_inputs_vars + loop_vars, loop):
            yield
            # Output the branch predicate and the inputs for the next iteration. Note
            # that we have to do fresh calls to `self.visit` here since we're in a new
            # context
            do_break = self.visit(break_predicate)
            loop.set_loop_outputs(do_break, *(self.visit(name) for name in loop_vars))
        # Update the DFG with the outputs from the loop
        for node, wire in zip(loop_vars, loop, strict=True):
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

    def _if_else(
        self,
        cond: ast.expr,
        inputs: list[PlaceNode],
        outputs: list[PlaceNode],
        only_true_inputs: list[PlaceNode] | None = None,
        only_false_inputs: list[PlaceNode] | None = None,
    ) -> tuple[AbstractContextManager[None], AbstractContextManager[None]]:
        """Builds a `Conditional`, returning context managers to build the `True` and
        `False` branch.
        """
        conditional = self.builder.add_conditional(
            self.visit(cond), *(self.visit(inp) for inp in inputs)
        )
        only_true_inputs_ = only_true_inputs or []
        only_false_inputs_ = only_false_inputs or []

        @contextmanager
        def true_case() -> Iterator[None]:
            with self._new_case(only_true_inputs_ + inputs, outputs, conditional, 1):
                yield

        @contextmanager
        def false_case() -> Iterator[None]:
            with self._new_case(only_false_inputs_ + inputs, outputs, conditional, 0):
                yield
            # Update the DFG with the outputs from the Conditional node
            for node, wire in zip(outputs, conditional, strict=True):
                self.dfg[node.place] = wire

        return true_case(), false_case()

    @contextmanager
    def _if_true(self, cond: ast.expr, inputs: list[PlaceNode]) -> Iterator[None]:
        """Context manager to build a graph inside the `true` case of a `Conditional`

        In the `false` case, the inputs are outputted as is.
        """
        true_case, false_case = self._if_else(cond, inputs, inputs)
        with false_case:
            # If the condition is false, output the inputs as is
            pass
        with true_case:
            # If the condition is true, we enter the `with` block
            yield

    def visit_Constant(self, node: ast.Constant) -> Wire:
        if value := python_value_to_hugr(node.value, get_type(node)):
            return self.builder.load(value)
        raise InternalGuppyError("Unsupported constant expression in compiler")

    def visit_PlaceNode(self, node: PlaceNode) -> Wire:
        if subscript := contains_subscript(node.place):
            if subscript.item not in self.dfg:
                self.dfg[subscript.item] = self.visit(subscript.item_expr)
            self.dfg[subscript] = self.visit(subscript.getitem_call)
        return self.dfg[node.place]

    def visit_GlobalName(self, node: GlobalName) -> Wire:
        defn = self.ctx.build_compiled_def(node.def_id)
        assert isinstance(defn, CompiledValueDef)
        if isinstance(defn, CompiledCallableDef) and defn.ty.parametrized:
            # TODO: This should be caught during checking
            err = UnsupportedError(
                node, "Polymorphic functions as dynamic higher-order values"
            )
            raise GuppyError(err)
        return defn.load(self.dfg, self.ctx, node)

    def visit_GenericParamValue(self, node: GenericParamValue) -> Wire:
        match node.param.ty:
            case NumericType(NumericType.Kind.Nat):
                arg = node.param.to_bound().to_hugr()
                load_nat = hugr.std.PRELUDE.get_op("load_nat").instantiate(
                    [arg], ht.FunctionType([], [ht.USize()])
                )
                usize = self.builder.add_op(load_nat)
                return self.builder.add_op(convert_ifromusize(), usize)
            case _:
                raise NotImplementedError

    def visit_Name(self, node: ast.Name) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_Tuple(self, node: ast.Tuple) -> Wire:
        elems = [self.visit(e) for e in node.elts]
        types = [get_type(e) for e in node.elts]
        return self._pack_tuple(elems, types)

    def visit_List(self, node: ast.List) -> Wire:
        # Note that this is a list literal (i.e. `[e1, e2, ...]`), not a comprehension
        inputs = [self.visit(e) for e in node.elts]
        list_ty = get_type(node)
        elem_ty = get_element_type(list_ty)
        return list_new(self.builder, elem_ty.to_hugr(), inputs)

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
            types = type_to_row(return_ty)
            assert len(returns) == len(types)
            return self._pack_tuple(returns, types)
        assert (
            len(returns) == 1
        ), f"Expected a single return value. Got {returns}. return type {return_ty}"
        return returns[0]

    def _update_inout_ports(
        self,
        args: list[ast.expr],
        inout_ports: Iterator[Wire],
        func_ty: FunctionType,
    ) -> None:
        """Helper method that updates the ports for borrowed arguments after a call."""
        for inp, arg in zip(func_ty.inputs, args, strict=True):
            if InputFlags.Inout in inp.flags:
                # Linearity checker ensures that borrowed arguments that are not places
                # can be safely dropped after the call returns
                if not isinstance(arg, PlaceNode):
                    next(inout_ports)
                    continue
                self.dfg[arg.place] = next(inout_ports)
                # Places involving subscripts need to generate code for the appropriate
                # `__setitem__` call. Nested subscripts are handled automatically since
                # `arg.place.parent` occurs as an arg of this call, so will also
                # be recursively reassigned.
                if subscript := contains_subscript(arg.place):
                    assert subscript.setitem_call is not None
                    # Need to assign __setitem__ value before compiling call.
                    # Note that the assignment to `self.dfg[arg.place]` also updated
                    # `self.dfg[subscript]` so that it now contains the value we want
                    # to write back into the subscript.
                    self.dfg[subscript.setitem_call.value_var] = self.dfg[subscript]
                    self.visit(subscript.setitem_call.call)
        assert next(inout_ports, None) is None, "Too many inout return ports"

    def visit_LocalCall(self, node: LocalCall) -> Wire:
        func = self.visit(node.func)
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)
        num_returns = len(type_to_row(func_ty.output))

        args = [self.visit(arg) for arg in node.args]
        call = self.builder.add_op(ops.CallIndirect(func_ty.to_hugr()), func, *args)
        regular_returns = list(call[:num_returns])
        inout_returns = call[num_returns:]
        self._update_inout_ports(node.args, inout_returns, func_ty)
        return self._pack_returns(regular_returns, func_ty.output)

    def visit_TensorCall(self, node: TensorCall) -> Wire:
        functions: Wire = self.visit(node.func)
        function_types = get_type(node.func)
        assert isinstance(function_types, TupleType)

        rets: list[Wire] = []
        remaining_args = node.args
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
        return self._pack_returns(rets, node.tensor_ty.output)

    def _compile_tensor_with_leftovers(
        self, func: Wire, func_ty: Type, args: list[ast.expr]
    ) -> tuple[
        list[Wire],  # Compiled outputs
        list[ast.expr],  # Leftover args
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
            input_len = len(func_ty.inputs)
            num_returns = len(type_to_row(func_ty.output))
            consumed_args, other_args = args[0:input_len], args[input_len:]
            consumed_wires = [self.visit(arg) for arg in consumed_args]
            call = self.builder.add_op(
                ops.CallIndirect(func_ty.to_hugr()), func, *consumed_wires
            )
            regular_returns: list[Wire] = list(call[:num_returns])
            inout_returns = call[num_returns:]
            self._update_inout_ports(consumed_args, inout_returns, func_ty)
            return regular_returns, other_args
        else:
            raise InternalGuppyError("Tensor element wasn't function or tuple")

    def visit_GlobalCall(self, node: GlobalCall) -> Wire:
        func = self.ctx.build_compiled_def(node.def_id)
        assert isinstance(func, CompiledCallableDef)

        args = [self.visit(arg) for arg in node.args]
        rets = func.compile_call(args, list(node.type_args), self.dfg, self.ctx, node)
        if isinstance(func, CustomFunctionDef) and not func.has_signature:
            func_ty = FunctionType(
                [FuncInput(get_type(arg), InputFlags.NoFlags) for arg in node.args],
                get_type(node),
            )
        else:
            func_ty = func.ty.instantiate(node.type_args)
        self._update_inout_ports(node.args, iter(rets.inout_returns), func_ty)
        return self._pack_returns(rets.regular_returns, func_ty.output)

    def visit_Call(self, node: ast.Call) -> Wire:
        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_PartialApply(self, node: PartialApply) -> Wire:
        func_ty = get_type(node.func)
        assert isinstance(func_ty, FunctionType)
        op = PartialOp.from_closure(
            func_ty.to_hugr(), [get_type(arg).to_hugr() for arg in node.args]
        )
        return self.builder.add_op(
            op, self.visit(node.func), *(self.visit(arg) for arg in node.args)
        )

    def visit_TypeApply(self, node: TypeApply) -> Wire:
        # For now, we can only TypeApply global FunctionDefs/Decls.
        if not isinstance(node.value, GlobalName):
            raise InternalGuppyError("Dynamic TypeApply not supported yet!")
        defn = self.ctx.build_compiled_def(node.value.def_id)
        assert isinstance(defn, CompiledCallableDef)

        # We have to be very careful here: If we instantiate `foo: forall T. T -> T`
        # with a tuple type `tuple[A, B]`, we get the type `tuple[A, B] -> tuple[A, B]`.
        # Normally, this would be represented in Hugr as a function with two output
        # ports types A and B. However, when TypeApplying `foo`, we actually get a
        # function with a single output port typed `tuple[A, B]`.
        # TODO: We would need to do manual monomorphisation in that case to obtain a
        #  function that returns two ports as expected
        if instantiation_needs_unpacking(defn.ty, node.inst):
            err = UnsupportedError(
                node, "Generic function instantiations returning rows"
            )
            raise GuppyError(err)

        return defn.load_with_args(node.inst, self.dfg, self.ctx, node)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Wire:
        # The only case that is not desugared by the type checker is the `not` operation
        # since it is not implemented via a dunder method
        if isinstance(node.op, ast.Not):
            arg = self.visit(node.operand)
            return self.builder.add_op(hugr.std.logic.Not, arg)

        raise InternalGuppyError("Node should have been removed during type checking.")

    def visit_FieldAccessAndDrop(self, node: FieldAccessAndDrop) -> Wire:
        struct_port = self.visit(node.value)
        field_idx = node.struct_ty.fields.index(node.field)
        return self._unpack_tuple(struct_port, [f.ty for f in node.struct_ty.fields])[
            field_idx
        ]

    def visit_SubscriptAccessAndDrop(self, node: SubscriptAccessAndDrop) -> Wire:
        self.dfg[node.item] = self.visit(node.item_expr)
        return self.visit(node.getitem_expr)

    def visit_ResultExpr(self, node: ResultExpr) -> Wire:
        value_wire = self.visit(node.value)
        base_ty = node.base_ty.to_hugr()
        extra_args: list[ht.TypeArg] = []
        if isinstance(node.base_ty, NumericType):
            match node.base_ty.kind:
                case NumericType.Kind.Nat:
                    base_name = "uint"
                    extra_args = [ht.BoundedNatArg(n=NumericType.INT_WIDTH)]
                case NumericType.Kind.Int:
                    base_name = "int"
                    extra_args = [ht.BoundedNatArg(n=NumericType.INT_WIDTH)]
                case NumericType.Kind.Float:
                    base_name = "f64"
                case kind:
                    assert_never(kind)
        else:
            # The only other valid base type is bool
            assert is_bool_type(node.base_ty)
            base_name = "bool"
        if node.array_len is not None:
            op_name = f"result_array_{base_name}"
            size_arg = node.array_len.to_arg().to_hugr()
            extra_args = [size_arg, *extra_args]
            hugr_ty: ht.Type = hugr.std.collections.array.Array(base_ty, size_arg)
            # Remove the option wrapping in the array
            unwrap = array_unwrap_elem(self.ctx)
            unwrap = self.builder.load_function(
                unwrap,
                instantiation=ht.FunctionType([ht.Option(base_ty)], [base_ty]),
                type_args=[ht.TypeTypeArg(base_ty)],
            )
            map_op = array_map(ht.Option(base_ty), size_arg, base_ty)
            value_wire = self.builder.add_op(map_op, value_wire, unwrap)
        else:
            op_name = f"result_{base_name}"
            hugr_ty = node.base_ty.to_hugr()
        op = tket2_result_op(
            op_name=op_name,
            typ=hugr_ty,
            tag=node.tag,
            extra_args=extra_args,
        )
        self.builder.add_op(op, value_wire)
        return self._pack_returns([], NoneType())

    def visit_PanicExpr(self, node: PanicExpr) -> Wire:
        err = build_error(self.builder, node.signal, node.msg)
        in_tys = [get_type(e).to_hugr() for e in node.values]
        out_tys = [ty.to_hugr() for ty in type_to_row(get_type(node))]
        args = [self.visit(e) for e in node.values]
        match node.kind:
            case ExitKind.Panic:
                h_node = build_panic(self.builder, in_tys, out_tys, err, *args)
            case ExitKind.ExitShot:
                op = panic(in_tys, out_tys, ExitKind.ExitShot)
                h_node = self.builder.add_op(op, err, *args)
        return self._pack_returns(list(h_node.outputs()), get_type(node))

    def visit_BarrierExpr(self, node: BarrierExpr) -> Wire:
        hugr_tys = [get_type(e).to_hugr() for e in node.args]
        op = hugr.std.prelude.PRELUDE_EXTENSION.get_op("Barrier").instantiate(
            [ht.SequenceArg([ht.TypeTypeArg(ty) for ty in hugr_tys])],
            ht.FunctionType.endo(hugr_tys),
        )

        barrier_n = self.builder.add_op(op, *(self.visit(e) for e in node.args))

        self._update_inout_ports(node.args, iter(barrier_n), node.func_ty)
        return self._pack_returns([], NoneType())

    def visit_DesugaredListComp(self, node: DesugaredListComp) -> Wire:
        # Make up a name for the list under construction and bind it to an empty list
        list_ty = get_type(node)
        assert isinstance(list_ty, OpaqueType)
        elem_ty = get_element_type(list_ty)
        list_place = Variable(next(tmp_vars), list_ty, node)
        self.dfg[list_place] = list_new(self.builder, elem_ty.to_hugr(), [])
        with self._build_generators(node.generators, [list_place]):
            elt_port = self.visit(node.elt)
            list_port = self.dfg[list_place]
            [], [self.dfg[list_place]] = self._build_method_call(
                list_ty, "append", node, [list_port, elt_port], list_ty.args
            )
        return self.dfg[list_place]

    def visit_DesugaredArrayComp(self, node: DesugaredArrayComp) -> Wire:
        # Allocate an uninitialised array of the desired size and a counter variable
        array_ty = get_type(node)
        assert isinstance(array_ty, OpaqueType)
        array_var = Variable(next(tmp_vars), array_ty, node)
        count_var = Variable(next(tmp_vars), int_type(), node)
        # See https://github.com/CQCL/guppylang/issues/629
        hugr_elt_ty = ht.Option(node.elt_ty.to_hugr())
        # Initialise array with `None`s
        make_none = array_comprehension_init_func(self.ctx)
        make_none = self.builder.load_function(
            make_none,
            instantiation=ht.FunctionType([], [hugr_elt_ty]),
            type_args=[ht.TypeTypeArg(node.elt_ty.to_hugr())],
        )
        self.dfg[array_var] = self.builder.add_op(
            array_repeat(hugr_elt_ty, node.length.to_arg().to_hugr()), make_none
        )
        self.dfg[count_var] = self.builder.load(
            hugr.std.int.IntVal(0, width=NumericType.INT_WIDTH)
        )
        with self._build_generators([node.generator], [array_var, count_var]):
            elt = self.visit(node.elt)
            array, count = self.dfg[array_var], self.dfg[count_var]
            [], [self.dfg[array_var]] = self._build_method_call(
                array_ty, "__setitem__", node, [array, count, elt], array_ty.args
            )
            # Update `count += 1`
            one = self.builder.load(hugr.std.int.IntVal(1, width=NumericType.INT_WIDTH))
            [self.dfg[count_var]], [] = self._build_method_call(
                int_type(), "__add__", node, [count, one]
            )
        return self.dfg[array_var]

    def _build_method_call(
        self,
        ty: Type,
        method: str,
        node: AstNode,
        args: list[Wire],
        type_args: Sequence[Argument] | None = None,
    ) -> CallReturnWires:
        func = self.ctx.get_instance_func(ty, method)
        assert func is not None
        return func.compile_call(args, type_args or [], self.dfg, self.ctx, node)

    @contextmanager
    def _build_generators(
        self, gens: list[DesugaredGenerator], loop_vars: list[Variable]
    ) -> Iterator[None]:
        """Context manager to build and enter the `TailLoop`s for a list of generators.

        The provided `loop_vars` will be threaded through and will be available inside
        the loops.
        """
        from guppylang.compiler.stmt_compiler import StmtCompiler

        compiler = StmtCompiler(self.ctx)
        with ExitStack() as stack:
            for gen in gens:
                # Build the generator
                compiler.compile_stmts([gen.iter_assign], self.dfg)
                assert isinstance(gen.iter, PlaceNode)
                iter_ty = get_type(gen.iter)
                inputs = [PlaceNode(place=var) for var in loop_vars]
                inputs += [
                    PlaceNode(place=place) for place in gen.borrowed_outer_places
                ]
                # Enter a new tail loop. Note that the iterator is a `just_input`, so
                # will not be outputted by the loop
                break_pred = PlaceNode(Variable(next(tmp_vars), bool_type(), gen.iter))
                stack.enter_context(self._new_loop([gen.iter], inputs, break_pred))
                # Enter a conditional checking if we have a next element
                next_ty = TupleType([get_type(gen.target), iter_ty])
                next_var = PlaceNode(Variable(next(tmp_vars), next_ty, gen.iter))
                hasnext_case, stop_case = self._if_else(
                    gen.next_call,
                    inputs,
                    only_true_inputs=[next_var],
                    outputs=[break_pred, *inputs],
                )
                # In the "no" case, we set the break predicate to true
                break_pred_hugr_ty = ht.Either([iter_ty.to_hugr()], [])
                with stop_case:
                    self.dfg[break_pred.place] = self.dfg.builder.add_op(
                        ops.Tag(1, break_pred_hugr_ty)
                    )
                # Otherwise, we continue, set the break predicate to false, and insert
                # the iterator for the next loop iteration
                stack.enter_context(hasnext_case)
                next_wire = self.dfg[next_var.place]
                elt, it = self.dfg.builder.add_op(ops.UnpackTuple(), next_wire)
                compiler.dfg = self.dfg
                compiler._assign(gen.target, elt)
                self.dfg[break_pred.place] = self.dfg.builder.add_op(
                    ops.Tag(0, break_pred_hugr_ty), it
                )
                # Enter nested conditionals for each if guard on the generator
                for if_expr in gen.ifs:
                    stack.enter_context(self._if_true(if_expr, [break_pred, *inputs]))
            # Yield control to the caller to build inside the loop
            yield

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
    match v:
        case bool():
            return hv.bool_value(v)
        case str():
            return hugr.std.prelude.StringVal(v)
        case int():
            return hugr.std.int.IntVal(v, width=NumericType.INT_WIDTH)
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
            assert is_frozenarray_type(exp_ty)
            elem_ty = get_element_type(exp_ty)
            vs = [python_value_to_hugr(elt, elem_ty) for elt in elts]
            if doesnt_contain_none(vs):
                return hugr.std.collections.static_array.StaticArrayVal(
                    vs, elem_ty.to_hugr(), name=f"static_pyarray.{next(tmp_vars)}"
                )
        case _:
            return None
    return None


def tket2_result_op(
    op_name: str,
    typ: ht.Type,
    tag: str,
    extra_args: Iterable[ht.TypeArg],
) -> ops.DataflowOp:
    """Creates a dummy operation for constructing a list."""
    args = [
        ht.StringArg(tag),
        *extra_args,
    ]
    sig = ht.FunctionType(
        input=[typ],
        output=[],
    )
    return ops.Custom(
        extension="tket2.result",
        op_name=op_name,
        args=args,
        signature=sig,
    )


ARRAY_COMPREHENSION_INIT: Final[GlobalConstId] = GlobalConstId.fresh(
    "array.__comprehension.init"
)
ARRAY_UNWRAP_ELEM: Final[GlobalConstId] = GlobalConstId.fresh("array.__unwrap_elem")


def array_comprehension_init_func(ctx: CompilerContext) -> hf.Function:
    """Returns the Hugr function that is used to initialise arrays elements before a
    comprehension.

    Just returns the `None` variant of the optional element type.

    See https://github.com/CQCL/guppylang/issues/629
    """
    v = ht.Variable(0, ht.TypeBound(ht.TypeBound.Any))
    sig = ht.PolyFuncType(
        params=[ht.TypeTypeParam(ht.TypeBound.Any)],
        body=ht.FunctionType([], [ht.Option(v)]),
    )
    func, already_defined = ctx.declare_global_func(ARRAY_COMPREHENSION_INIT, sig)
    if not already_defined:
        func.set_outputs(func.add_op(ops.Tag(0, ht.Option(v))))
    return func


def array_unwrap_elem(ctx: CompilerContext) -> hf.Function:
    """Returns the Hugr function that is used to unwrap the elements in an option array
    to turn it into a regular array."""
    v = ht.Variable(0, ht.TypeBound(ht.TypeBound.Any))
    sig = ht.PolyFuncType(
        params=[ht.TypeTypeParam(ht.TypeBound.Any)],
        body=ht.FunctionType([ht.Option(v)], [v]),
    )
    func, already_defined = ctx.declare_global_func(ARRAY_UNWRAP_ELEM, sig)
    if not already_defined:
        msg = "Linear array element has already been used"
        func.set_outputs(build_unwrap(func, func.inputs()[0], msg))
    return func


T = TypeVar("T")


def doesnt_contain_none(xs: list[T | None]) -> TypeGuard[list[T]]:
    """Checks if a list contains `None`."""
    return all(x is not None for x in xs)
