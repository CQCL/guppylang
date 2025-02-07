"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from typing import Final

import hugr.build.function as hf
from hugr import Node, Wire, ops
from hugr import tys as ht
from hugr.std.collections.array import EXTENSION

from guppylang.compiler.core import (
    GlobalConstId,
)
from guppylang.definition.custom import CustomCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.std._internal.compiler.arithmetic import INT_T, convert_itousize
from guppylang.std._internal.compiler.prelude import (
    build_expect_none,
    build_unwrap,
    build_unwrap_left,
    build_unwrap_right,
)
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.builtin import int_type

# ------------------------------------------------------
# --------------- std.array operations -----------------
# ------------------------------------------------------


def _instantiate_array_op(
    name: str,
    elem_ty: ht.Type,
    length: ht.TypeArg,
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.ExtOp:
    return EXTENSION.get_op(name).instantiate(
        [length, ht.TypeTypeArg(elem_ty)], ht.FunctionType(inp, out)
    )


def array_type(elem_ty: ht.Type, length: ht.TypeArg) -> ht.ExtType:
    """Returns the hugr type of a fixed length array."""
    elem_arg = ht.TypeTypeArg(elem_ty)
    return EXTENSION.types["array"].instantiate([length, elem_arg])


def array_new(elem_ty: ht.Type, length: int) -> ops.ExtOp:
    """Returns an operation that creates a new fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    return _instantiate_array_op(
        "new_array", elem_ty, length_arg, [elem_ty] * length, [arr_ty]
    )


def array_get(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `get` operation."""
    assert elem_ty.type_bound() == ht.TypeBound.Copyable
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "get", elem_ty, length, [arr_ty, ht.USize()], [ht.Option(elem_ty)]
    )


def array_set(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `set` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "set",
        elem_ty,
        length,
        [arr_ty, ht.USize(), elem_ty],
        [ht.Either([elem_ty, arr_ty], [elem_ty, arr_ty])],
    )


def array_pop(elem_ty: ht.Type, length: int, from_left: bool) -> ops.ExtOp:
    """Returns an operation that pops an element from the left of an array."""
    assert length > 0
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    popped_arr_ty = array_type(elem_ty, ht.BoundedNatArg(length - 1))
    op = "pop_left" if from_left else "pop_right"
    return _instantiate_array_op(
        op, elem_ty, length_arg, [arr_ty], [ht.Option(elem_ty, popped_arr_ty)]
    )


def array_discard_empty(elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that discards an array of length zero."""
    arr_ty = array_type(elem_ty, ht.BoundedNatArg(0))
    return EXTENSION.get_op("discard_empty").instantiate(
        [ht.TypeTypeArg(elem_ty)], ht.FunctionType([arr_ty], [])
    )


def array_scan(
    elem_ty: ht.Type,
    length: ht.TypeArg,
    new_elem_ty: ht.Type,
    accumulators: list[ht.Type],
) -> ops.ExtOp:
    """Returns an operation that maps and folds a function across an array."""
    ty_args = [
        length,
        ht.TypeTypeArg(elem_ty),
        ht.TypeTypeArg(new_elem_ty),
        ht.SequenceArg([ht.TypeTypeArg(acc) for acc in accumulators]),
        ht.ExtensionsArg([]),
    ]
    ins = [
        array_type(elem_ty, length),
        ht.FunctionType([elem_ty, *accumulators], [new_elem_ty, *accumulators]),
        *accumulators,
    ]
    outs = [array_type(new_elem_ty, length), *accumulators]
    return EXTENSION.get_op("scan").instantiate(ty_args, ht.FunctionType(ins, outs))


def array_map(elem_ty: ht.Type, length: ht.TypeArg, new_elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that maps a function across an array."""
    return array_scan(elem_ty, length, new_elem_ty, accumulators=[])


def array_repeat(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `repeat` operation."""
    return EXTENSION.get_op("repeat").instantiate(
        [length, ht.TypeTypeArg(elem_ty), ht.ExtensionsArg([])],
        ht.FunctionType(
            [ht.FunctionType([], [elem_ty])], [array_type(elem_ty, length)]
        ),
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class ArrayCompiler(CustomCallCompiler):
    """Base class for custom array op compilers."""

    @property
    def elem_ty(self) -> ht.Type:
        """The element type for the array op that is being compiled."""
        match self.type_args:
            case [TypeArg(ty=elem_ty), _]:
                return elem_ty.to_hugr()
            case _:
                raise InternalGuppyError("Invalid array type args")

    @property
    def length(self) -> ht.TypeArg:
        """The length for the array op that is being compiled."""
        match self.type_args:
            case [_, ConstArg(const)]:  # Const includes both literals and variables
                return const.to_arg().to_hugr()
            case _:
                raise InternalGuppyError("Invalid array type args")


class NewArrayCompiler(ArrayCompiler):
    """Compiler for the `array.__new__` function."""

    def build_classical_array(self, elems: list[Wire]) -> Wire:
        """Lowers a call to `array.__new__` for classical arrays."""
        # See https://github.com/CQCL/guppylang/issues/629
        return self.build_linear_array(elems)

    def build_linear_array(self, elems: list[Wire]) -> Wire:
        """Lowers a call to `array.__new__` for linear arrays."""
        elem_opts = [
            self.builder.add_op(ops.Some(self.elem_ty), elem) for elem in elems
        ]
        return self.builder.add_op(
            array_new(ht.Option(self.elem_ty), len(elems)), *elem_opts
        )

    def compile(self, args: list[Wire]) -> list[Wire]:
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            return [self.build_linear_array(args)]
        else:
            return [self.build_classical_array(args)]


ARRAY_GETITEM_CLASSICAL: Final[GlobalConstId] = GlobalConstId.fresh()
ARRAY_GETITEM_LINEAR: Final[GlobalConstId] = GlobalConstId.fresh()
ARRAY_SETITEM_CLASSICAL: Final[GlobalConstId] = GlobalConstId.fresh()
ARRAY_SETITEM_LINEAR: Final[GlobalConstId] = GlobalConstId.fresh()


class ArrayGetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__getitem__` function."""

    def _getitem_ty(self, bound: ht.TypeBound) -> ht.PolyFuncType:
        """Constructs a polymorphic function type for `__getitem__`"""
        # a(Option(T), N), int -> T, a(Option(T), N)
        # Array element type parameter
        elem_ty_param = ht.TypeTypeParam(bound)
        # Array length parameter
        length_param = ht.BoundedNatParam()
        return ht.PolyFuncType(
            params=[elem_ty_param, length_param],
            body=ht.FunctionType(
                input=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                    int_type().to_hugr(),
                ],
                output=[
                    ht.Variable(0, bound),
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                ],
            ),
        )

    def _build_classical_getitem(self, name: str) -> Wire:
        """Constructs a generic function for `__getitem__` for classical arrays."""
        func_ty = self._getitem_ty(ht.TypeBound.Copyable)
        func = self.ctx.module.define_function(
            name=name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )

        elem_ty = ht.Variable(0, ht.TypeBound.Copyable)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        # See https://github.com/CQCL/guppylang/issues/629
        elem_opt_ty = ht.Option(elem_ty)
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_get(elem_opt_ty, length),
            func.inputs()[0],
            idx,
        )
        elem_opt = build_unwrap(func, result, "Array index out of bounds")
        elem = build_unwrap(func, elem_opt, "array.__getitem__: Internal error")

        # Return input array unmodified for consistency with linear implementation.
        func.set_outputs(elem, func.inputs()[0])
        return func.parent_node

    def _build_linear_getitem(self, name: str) -> Wire:
        """Constructs function to call `array.__getitem__` for linear arrays."""
        func_ty = self._getitem_ty(ht.TypeBound.Any)
        func = self.ctx.module.define_function(
            name=name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )

        elem_ty = ht.Variable(0, ht.TypeBound.Any)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        none = func.add_op(ops.Tag(0, elem_opt_ty))
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            none,
        )
        elem_opt, array = build_unwrap_right(func, result, "Array index out of bounds")
        elem = build_unwrap(
            func, elem_opt, "Linear array element has already been used"
        )

        func.set_outputs(elem, array)
        return func.parent_node

    def _build_call_getitem(
        self,
        func: Wire,
        array: Wire,
        idx: Wire,
    ) -> CallReturnWires:
        """Inserts a call to `array.__getitem__`."""
        concrete_func_ty = ht.FunctionType(
            input=[array_type(ht.Option(self.elem_ty), self.length), int_type().to_hugr()],
            output=[self.elem_ty, array_type(ht.Option(self.elem_ty), self.length)],
        )
        type_args = [ht.TypeTypeArg(self.elem_ty), self.length]
        assert isinstance(func, Node)
        func_call = self.builder.call(
            func,
            array,
            idx,
            instantiation=concrete_func_ty,
            type_args=type_args,
        )
        outputs = list(func_call.outputs())
        return CallReturnWires(
            regular_returns=[outputs[0]],
            inout_returns=[outputs[1]],
        )

    def compile_classical_getitem(self, array: Wire, idx: Wire) -> CallReturnWires:
        """Lowers a call to `array.__getitem__` for classical arrays."""
        if ARRAY_GETITEM_CLASSICAL not in self.ctx.global_consts:
            self.ctx.global_consts[ARRAY_GETITEM_CLASSICAL] = (
                self._build_classical_getitem(
                    name=ARRAY_GETITEM_CLASSICAL.name("array.__getitem__.classical")
                )
            )
        return self._build_call_getitem(
            func=self.ctx.global_consts[ARRAY_GETITEM_CLASSICAL],
            array=array,
            idx=idx,
        )

    def compile_linear_getitem(self, array: Wire, idx: Wire) -> CallReturnWires:
        """Lowers a call to `array.__getitem__` for classical arrays."""
        if ARRAY_GETITEM_LINEAR not in self.ctx.global_consts:
            self.ctx.global_consts[ARRAY_GETITEM_LINEAR] = (
                self._build_linear_getitem(
                    name=ARRAY_GETITEM_LINEAR.name("array.__getitem__.linear")
                )
            )
        return self._build_call_getitem(
            func=self.ctx.global_consts[ARRAY_GETITEM_LINEAR],
            array=array,
            idx=idx,
        )

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx] = args
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            return self.compile_linear_getitem(array, idx)
        else:
            return self.compile_classical_getitem(array, idx)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArraySetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__setitem__` function."""

    def _setitem_ty(self, bound: ht.TypeBound) -> ht.PolyFuncType:
        """Constructs a polymorphic function type for `__setitem__`"""
        # a(Option(T), N), int, T -> a(Option(T), N)
        elem_ty_param = ht.TypeTypeParam(bound)
        length_param = ht.BoundedNatParam()
        return ht.PolyFuncType(
            params=[elem_ty_param, length_param],
            body=ht.FunctionType(
                input=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                    int_type().to_hugr(),
                    ht.Variable(0, bound),
                ],
                output=[
                    array_type(
                        ht.Option(ht.Variable(0, bound)),
                        ht.VariableArg(1, length_param),
                    ),
                ],
            ),
        )

    def _build_classical_setitem(self, name: str) -> Wire:
        """Constructs a generic function for `__setitem__` for classical arrays."""
        func_ty = self._setitem_ty(ht.TypeBound.Copyable)
        func = self.ctx.module.define_function(
            name=name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )

        elem_ty = ht.Variable(0, ht.TypeBound.Copyable)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        elem_opt = func.add_op(ops.Some(elem_ty), func.inputs()[2])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            elem_opt,
        )
        _, array = build_unwrap_right(func, result, "Array index out of bounds")

        func.set_outputs(array)
        return func.parent_node

    def _build_linear_setitem(self, name: str) -> Wire:
        """Constructs function to call `array.__setitem__` for linear arrays."""
        func_ty = self._setitem_ty(ht.TypeBound.Any)
        func = self.ctx.module.define_function(
            name=name,
            input_types=func_ty.body.input,
            output_types=func_ty.body.output,
            type_params=func_ty.params,
        )

        elem_ty = ht.Variable(0, ht.TypeBound.Any)
        length = ht.VariableArg(1, ht.BoundedNatParam())

        elem_opt_ty = ht.Option(elem_ty)
        elem = func.add_op(ops.Some(elem_ty), func.inputs()[2])
        idx = func.add_op(convert_itousize(), func.inputs()[1])
        result = func.add_op(
            array_set(elem_opt_ty, length),
            func.inputs()[0],
            idx,
            elem,
        )
        old_elem_opt, array = build_unwrap_right(
            func, result, "Array index out of bounds"
        )
        build_unwrap_left(func, old_elem_opt, "Linear array element has not been used")

        func.set_outputs(array)
        return func.parent_node

    def _build_call_setitem(
        self,
        func: Wire,
        array: Wire,
        idx: Wire,
        elem: Wire,
    ) -> CallReturnWires:
        """Inserts a call to `array.__setitem__`."""
        concrete_func_ty = ht.FunctionType(
            input=[
                array_type(ht.Option(self.elem_ty), self.length),
                int_type().to_hugr(),
                self.elem_ty,
            ],
            output=[array_type(ht.Option(self.elem_ty), self.length)],
        )
        type_args = [ht.TypeTypeArg(self.elem_ty), self.length]
        assert isinstance(func, Node)
        func_call = self.builder.call(
            func,
            array,
            idx,
            elem,
            instantiation=concrete_func_ty,
            type_args=type_args,
        )
        return CallReturnWires(
            regular_returns=[],
            inout_returns=list(func_call.outputs()),
        )

    def compile_classical_setitem(
        self, array: Wire, idx: Wire, elem: Wire
    ) -> CallReturnWires:
        """Lowers a call to `array.__setitem__` for classical arrays."""
        if ARRAY_SETITEM_CLASSICAL not in self.ctx.global_consts:
            self.ctx.global_consts[ARRAY_SETITEM_CLASSICAL] = (
                self._build_classical_setitem(
                    name=ARRAY_SETITEM_CLASSICAL.name("array.__setitem__.classical")
                )
            )
        return self._build_call_setitem(
            func=self.ctx.global_consts[ARRAY_SETITEM_CLASSICAL],
            array=array,
            idx=idx,
            elem=elem,
        )

    def compile_linear_setitem(
        self, array: Wire, idx: Wire, elem: Wire
    ) -> CallReturnWires:
        """Lowers a call to `array.__setitem__` for linear arrays."""
        if ARRAY_SETITEM_LINEAR not in self.ctx.global_consts:
            self.ctx.global_consts[ARRAY_SETITEM_LINEAR] = (
                self._build_linear_setitem(
                    name=ARRAY_SETITEM_LINEAR.name("array.__setitem__.linear")
                )
            )
        return self._build_call_setitem(
            func=self.ctx.global_consts[ARRAY_SETITEM_LINEAR],
            array=array,
            idx=idx,
            elem=elem,
        )

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx, elem] = args
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            return self.compile_linear_setitem(array, idx, elem)
        else:
            return self.compile_classical_setitem(array, idx, elem)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArrayIterEndCompiler(ArrayCompiler):
    """Compiler for the `ArrayIter.__end__` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        # For linear array iterators, map the array of optional elements to an
        # `array[None, n]` that we can discard.
        if self.elem_ty.type_bound() == ht.TypeBound.Any:
            elem_opt_ty = ht.Option(self.elem_ty)
            none_ty = ht.UnitSum(1)
            # Define `unwrap_none` function. If any of the elements are not `None`,
            # then the users must have called `__end__` prematurely and we panic.
            func = self.builder.define_function("unwrap_none", [elem_opt_ty], [none_ty])
            err_msg = "Linear array element has not been used in iterator"
            build_expect_none(func, func.inputs()[0], err_msg)
            func.set_outputs(func.add_op(ops.Tag(0, none_ty)))
            func = self.builder.load_function(func)
            # Map it over the array so that the resulting array is no longer linear and
            # can be discarded
            [array_iter] = args
            array, _ = self.builder.add_op(ops.UnpackTuple(), array_iter)
            self.builder.add_op(
                array_map(elem_opt_ty, self.length, none_ty), array, func
            )
        return []
