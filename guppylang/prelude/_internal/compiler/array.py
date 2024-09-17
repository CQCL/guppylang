"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import hugr.std
from hugr import Wire, ops
from hugr import tys as ht

from guppylang.definition.custom import CustomCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.prelude._internal.compiler.arithmetic import convert_itousize
from guppylang.prelude._internal.compiler.prelude import build_error, build_panic
from guppylang.tys.arg import ConstArg, TypeArg
from guppylang.tys.const import ConstValue

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase


def array_type(length: int, elem_ty: ht.Type) -> ht.ExtType:
    """Returns the hugr type of a fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    elem_arg = ht.TypeTypeArg(elem_ty)
    return hugr.std.PRELUDE.types["array"].instantiate([length_arg, elem_arg])


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class NewArrayCompiler(CustomCallCompiler):
    """Compiler for the `array.__new__` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        match self.type_args:
            case [TypeArg(ty=elem_ty), ConstArg(ConstValue(value=int(length)))]:
                op = new_array(length, elem_ty.to_hugr())
                return [self.builder.add_op(op, *args)]
            case type_args:
                raise InternalGuppyError(f"Invalid array type args: {type_args}")


class ArrayGetitemCompiler(CustomCallCompiler):
    """Compiler for the `array.__getitem__` function."""

    def build_classical_getitem(
        self,
        array: Wire,
        array_ty: ht.Type,
        idx: Wire,
        idx_ty: ht.Type,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `array.__getitem__` for classical arrays."""
        length = self.type_args[1].to_hugr()
        elem = build_array_get(
            self.builder, array, array_ty, idx, idx_ty, elem_ty, length
        )
        return CallReturnWires(regular_returns=[elem], inout_returns=[array])

    def build_linear_getitem(
        self,
        array: Wire,
        array_ty: ht.Type,
        idx: Wire,
        idx_ty: ht.Type,
        elem_ty: ht.Type,
    ) -> CallReturnWires:
        """Lowers a call to `array.__getitem__` for linear arrays."""
        # Swap out the element at the given index with `None`. The `to_hugr`
        # implementation of the array type ensures that linear element types are turned
        # into optionals.
        elem_opt_ty = ht.Sum([[elem_ty], []])
        none = self.builder.add_op(ops.Tag(1, elem_opt_ty))
        length = self.type_args[1].to_hugr()
        array, elem_opt = build_array_set(
            self.builder,
            array,
            array_ty,
            idx,
            idx_ty,
            none,
            elem_opt_ty,
            length,
        )
        # Make sure that the element we got out is not None
        conditional = self.builder.add_conditional(elem_opt)
        with conditional.add_case(0) as case:
            case.set_outputs(*case.inputs())
        with conditional.add_case(1) as case:
            error = build_error(case, 1, "Linear array element has already been used")
            case.set_outputs(*build_panic(case, [], [elem_ty], error))
        return CallReturnWires(regular_returns=[conditional], inout_returns=[array])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx] = args
        [array_ty, idx_ty] = self.ty.input
        [elem_ty, *_] = self.ty.output
        if elem_ty.type_bound() == ht.TypeBound.Any:
            return self.build_linear_getitem(array, array_ty, idx, idx_ty, elem_ty)
        else:
            return self.build_classical_getitem(array, array_ty, idx, idx_ty, elem_ty)

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


class ArraySetitemCompiler(CustomCallCompiler):
    """Compiler for the `array.__setitem__` function."""

    def build_classical_setitem(
        self,
        array: Wire,
        array_ty: ht.Type,
        idx: Wire,
        idx_ty: ht.Type,
        elem: Wire,
        elem_ty: ht.Type,
        length: ht.TypeArg,
    ) -> CallReturnWires:
        """Lowers a call to `array.__setitem__` for classical arrays."""
        array, _ = build_array_set(
            self.builder, array, array_ty, idx, idx_ty, elem, elem_ty, length
        )
        return CallReturnWires(regular_returns=[], inout_returns=[array])

    def build_linear_setitem(
        self,
        array: Wire,
        array_ty: ht.Type,
        idx: Wire,
        idx_ty: ht.Type,
        elem: Wire,
        elem_ty: ht.Type,
        length: ht.TypeArg,
    ) -> CallReturnWires:
        """Lowers a call to `array.__setitem__` for linear arrays."""
        # Embed the element into an optional
        elem_opt_ty = ht.Sum([[elem_ty], []])
        elem = self.builder.add_op(ops.Tag(0, elem_opt_ty), elem)
        array, old_elem = build_array_set(
            self.builder, array, array_ty, idx, idx_ty, elem, elem_opt_ty, length
        )
        # Check that the old element was `None`
        conditional = self.builder.add_conditional(old_elem)
        with conditional.add_case(0) as case:
            error = build_error(case, 1, "Linear array element has not been used")
            build_panic(case, [elem_ty], [], error, *case.inputs())
            case.set_outputs()
        with conditional.add_case(1) as case:
            case.set_outputs()
        return CallReturnWires(regular_returns=[], inout_returns=[array])

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        [array, idx, elem] = args
        [array_ty, idx_ty, elem_ty] = self.ty.input
        length = self.type_args[1].to_hugr()
        if elem_ty.type_bound() == ht.TypeBound.Any:
            return self.build_linear_setitem(
                array, array_ty, idx, idx_ty, elem, elem_ty, length
            )
        else:
            return self.build_classical_setitem(
                array, array_ty, idx, idx_ty, elem, elem_ty, length
            )

    def compile(self, args: list[Wire]) -> list[Wire]:
        raise InternalGuppyError("Call compile_with_inouts instead")


def build_array_set(
    builder: DfBase[ops.DfParentOp],
    array: Wire,
    array_ty: ht.Type,
    idx: Wire,
    idx_ty: ht.Type,
    elem: Wire,
    elem_ty: ht.Type,
    length: ht.TypeArg,
) -> tuple[Wire, Wire]:
    """Builds an array set operation, returning the original element."""
    sig = ht.FunctionType(
        [array_ty, ht.USize(), elem_ty],
        [ht.Sum([[elem_ty, array_ty], [elem_ty, array_ty]])],
    )
    if idx_ty != ht.USize():
        idx = builder.add_op(convert_itousize(), idx)
    op = ops.ExtOp(
        hugr.std.PRELUDE.get_op("set"), sig, [length, ht.TypeTypeArg(elem_ty)]
    )
    [result] = builder.add_op(op, array, idx, elem)
    conditional = builder.add_conditional(result)
    with conditional.add_case(0) as case:
        error = build_error(case, 1, "array set index out of bounds")
        case.set_outputs(
            *build_panic(
                case, [elem_ty, array_ty], [elem_ty, array_ty], error, *case.inputs()
            )
        )
    with conditional.add_case(1) as case:
        case.set_outputs(*case.inputs())
    [elem, array] = conditional
    return (array, elem)


def build_array_get(
    builder: DfBase[ops.DfParentOp],
    array: Wire,
    array_ty: ht.Type,
    idx: Wire,
    idx_ty: ht.Type,
    elem_ty: ht.Type,
    length: ht.TypeArg,
) -> Wire:
    """Builds an array get operation, returning the original element."""
    sig = ht.FunctionType([array_ty, ht.USize()], [ht.Sum([[], [elem_ty]])])
    op = ops.ExtOp(
        hugr.std.PRELUDE.get_op("get"), sig, [length, ht.TypeTypeArg(elem_ty)]
    )
    if idx_ty != ht.USize():
        idx = builder.add_op(convert_itousize(), idx)
    [result] = builder.add_op(op, array, idx)
    conditional = builder.add_conditional(result)
    with conditional.add_case(0) as case:
        error = build_error(case, 1, "array get index out of bounds")
        case.set_outputs(*build_panic(case, [], [elem_ty], error))
    with conditional.add_case(1) as case:
        case.set_outputs(*case.inputs())
    return conditional


def new_array(length: int, elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that creates a new fixed length array."""
    op_def = hugr.std.PRELUDE.get_op("new_array")
    sig = ht.FunctionType([elem_ty] * length, [array_type(length, elem_ty)])
    return ops.ExtOp(op_def, sig, [ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)])
