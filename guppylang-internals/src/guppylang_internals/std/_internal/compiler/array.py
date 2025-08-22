"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypeVar

import hugr
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections.borrow_array import EXTENSION

from guppylang_internals.compiler.core import (
    GlobalConstId,
)
from guppylang_internals.definition.custom import CustomCallCompiler
from guppylang_internals.definition.value import CallReturnWires
from guppylang_internals.error import InternalGuppyError
from guppylang_internals.std._internal.compiler.arithmetic import convert_itousize
from guppylang_internals.std._internal.compiler.prelude import (
    build_unwrap_right,
)
from guppylang_internals.tys.arg import ConstArg, TypeArg
from guppylang_internals.tys.builtin import int_type

if TYPE_CHECKING:
    from hugr.build import function as hf
    from hugr.build.dfg import DfBase


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
    """Returns the hugr type of a fixed length array.

    This is the `borrow_array` type used by Guppy.
    """
    elem_arg = ht.TypeTypeArg(elem_ty)
    return EXTENSION.types["borrow_array"].instantiate([length, elem_arg])


def standard_array_type(elem_ty: ht.Type, length: ht.TypeArg) -> ht.ExtType:
    """Returns the hugr type of a linear fixed length array.

    This is the standard `array` type targeted by Hugr.
    """
    elem_arg = ht.TypeTypeArg(elem_ty)
    defn = hugr.std.collections.array.EXTENSION.types["array"]
    return defn.instantiate([length, elem_arg])


def array_new(elem_ty: ht.Type, length: int) -> ops.ExtOp:
    """Returns an operation that creates a new fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    return _instantiate_array_op(
        "new_array", elem_ty, length_arg, [elem_ty] * length, [arr_ty]
    )


def array_unpack(elem_ty: ht.Type, length: int) -> ops.ExtOp:
    """Returns an operation that unpacks a fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    arr_ty = array_type(elem_ty, length_arg)
    return _instantiate_array_op(
        "unpack", elem_ty, length_arg, [arr_ty], [elem_ty] * length
    )


def array_get(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `get` operation."""
    assert elem_ty.type_bound() == ht.TypeBound.Copyable
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "get", elem_ty, length, [arr_ty, ht.USize()], [ht.Option(elem_ty), arr_ty]
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
        ht.ListArg([ht.TypeTypeArg(acc) for acc in accumulators]),
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
        [length, ht.TypeTypeArg(elem_ty)],
        ht.FunctionType(
            [ht.FunctionType([], [elem_ty])], [array_type(elem_ty, length)]
        ),
    )


def array_convert_to_std_array(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array operation to convert the `borrow_array` type used by Guppy into
    the regular `array` in Hugr.
    """
    return EXTENSION.get_op("to_array").instantiate(
        [length, ht.TypeTypeArg(elem_ty)],
        ht.FunctionType(
            [array_type(elem_ty, length)], [standard_array_type(elem_ty, length)]
        ),
    )


def array_convert_from_std_array(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array operation to convert the `array` type used by Hugr into the
    `borrow_array` type used by Guppy.
    """
    return EXTENSION.get_op("from_array").instantiate(
        [length, ht.TypeTypeArg(elem_ty)],
        ht.FunctionType(
            [standard_array_type(elem_ty, length)], [array_type(elem_ty, length)]
        ),
    )


def array_borrow(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `borrow` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "borrow", elem_ty, length, [arr_ty, ht.USize()], [elem_ty, arr_ty]
    )


def array_return(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `return` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op(
        "return", elem_ty, length, [arr_ty, ht.USize(), elem_ty], [arr_ty]
    )


def array_discard_all_borrowed(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `borrow` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op("discard_all_borrowed", elem_ty, length, [arr_ty], [])


def array_new_all_borrowed(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `borrow` operation."""
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op("new_all_borrowed", elem_ty, length, [], [arr_ty])


def array_clone(elem_ty: ht.Type, length: ht.TypeArg) -> ops.ExtOp:
    """Returns an array `clone` operation."""
    assert elem_ty.type_bound() == ht.TypeBound.Copyable
    arr_ty = array_type(elem_ty, length)
    return _instantiate_array_op("clone", elem_ty, length, [arr_ty], [arr_ty, arr_ty])


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


P = TypeVar("P", bound=ops.DfParentOp)


def unpack_array(builder: DfBase[P], array: Wire) -> list[Wire]:
    """Unpacks a fixed length array into its elements."""
    array_ty = builder.hugr.port_type(array.out_port())
    assert isinstance(array_ty, ht.ExtType)
    match array_ty.args:
        case [ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)]:
            res = builder.add_op(array_unpack(elem_ty, length), array)
            return [res[i] for i in range(length)]
        case _:
            raise InternalGuppyError("Invalid array type args")


class ArrayCompiler(CustomCallCompiler):
    """Base class for custom array op compilers."""

    @property
    def elem_ty(self) -> ht.Type:
        """The element type for the array op that is being compiled."""
        match self.type_args:
            case [TypeArg(ty=elem_ty), _]:
                return elem_ty.to_hugr(self.ctx)
            case _:
                raise InternalGuppyError("Invalid array type args")

    @property
    def length(self) -> ht.TypeArg:
        """The length for the array op that is being compiled."""
        match self.type_args:
            case [_, ConstArg(const)]:  # Const includes both literals and variables
                return const.to_arg().to_hugr(self.ctx)
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
        return self.builder.add_op(array_new(self.elem_ty, len(elems)), *elems)

    def compile(self, args: list[Wire]) -> list[Wire]:
        if self.elem_ty.type_bound() == ht.TypeBound.Linear:
            return [self.build_linear_array(args)]
        else:
            return [self.build_classical_array(args)]


class ArrayGetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__getitem__` function."""

    def _build_classical_getitem(self, array: Wire, idx: Wire) -> None:
        """Constructs `__getitem__` for classical arrays."""
        idx = self.builder.add_op(convert_itousize(), idx)

        # As copyable elements can be used multiple times, we need to swap the element
        # back after initially borrowing it to get the value.
        # (`array_get` cannot be used to to current bool lowering limitations)
        elem, arr = self.builder.add_op(
            array_borrow(self.elem_ty, self.length),
            array,
            idx,
        )
        arr = self.builder.add_op(
            array_return(self.elem_ty, self.length),
            arr,
            idx,
            elem,
        )

        return CallReturnWires(
            regular_returns=[elem],
            inout_returns=[arr],
        )

    def _build_linear_getitem(self, array: Wire, idx: Wire) -> None:
        """Constructs `array.__getitem__` for linear arrays."""
        idx = self.builder.add_op(convert_itousize(), idx)
        elem, arr = self.builder.add_op(
            array_borrow(self.elem_ty, self.length),
            array,
            idx,
        )
        return CallReturnWires(
            regular_returns=[elem],
            inout_returns=[arr],
        )

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx] = args
        [elem_ty_arg, _] = self.type_args
        assert isinstance(elem_ty_arg, TypeArg)
        if not elem_ty_arg.ty.copyable:
            return self._build_linear_getitem(array, idx)
        else:
            return self._build_classical_getitem(array, idx)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArraySetitemCompiler(ArrayCompiler):
    """Compiler for the `array.__setitem__` function."""

    def _build_classical_setitem(self, array: Wire, idx: Wire, elem: Wire) -> None:
        """Constructs `__setitem__` for classical arrays."""
        idx = self.builder.add_op(convert_itousize(), idx)
        result = self.builder.add_op(
            array_set(self.elem_ty, self.length),
            array,
            idx,
            elem,
        )
        _, arr = build_unwrap_right(self.builder, result, "Array index out of bounds")

        return CallReturnWires(
            regular_returns=[],
            inout_returns=[arr],
        )

    def _build_linear_setitem(self, array: Wire, idx: Wire, elem: Wire) -> None:
        """Constructs `array.__setitem__` for linear arrays."""
        idx = self.builder.add_op(convert_itousize(), idx)
        arr = self.builder.add_op(
            array_return(self.elem_ty, self.length),
            array,
            idx,
            elem,
        )

        return CallReturnWires(
            regular_returns=[],
            inout_returns=[arr],
        )

    def _build_call_setitem(
        self,
        func: hf.Function,
        array: Wire,
        idx: Wire,
        elem: Wire,
    ) -> CallReturnWires:
        """Inserts a call to `array.__setitem__`."""
        concrete_func_ty = ht.FunctionType(
            input=[
                array_type(self.elem_ty, self.length),
                int_type().to_hugr(self.ctx),
                self.elem_ty,
            ],
            output=[array_type(self.elem_ty, self.length)],
        )
        type_args = [ht.TypeTypeArg(self.elem_ty), self.length]
        func_call = self.builder.call(
            func.parent_node,
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

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx, elem] = args
        if self.elem_ty.type_bound() == ht.TypeBound.Linear:
            return self._build_linear_setitem(array, idx, elem)
        else:
            return self._build_classical_setitem(array, idx, elem)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


ARRAY_ITER_ASSERT_ALL_USED_HELPER: Final[GlobalConstId] = GlobalConstId.fresh(
    "ArrayIter._assert_all_used.helper"
)


class ArrayIterAsertAllUsedCompiler(ArrayCompiler):
    """Compiler for the `ArrayIter._assert_all_used` method."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        if self.elem_ty.type_bound() == ht.TypeBound.Linear:
            [array_iter] = args
            self.builder.add_op(
                array_discard_all_borrowed(self.elem_ty, self.length),
                array_iter,
            )
        return []
