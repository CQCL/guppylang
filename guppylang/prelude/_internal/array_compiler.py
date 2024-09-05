"""Compilers building array functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hugr import Wire, ops
from hugr import tys as ht

from guppylang.compiler.hugr_extension import UnsupportedOp
from guppylang.definition.custom import CustomCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.error import InternalGuppyError
from guppylang.prelude._internal.compiler import build_error, build_panic

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase


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
        [ty_arg, len_arg] = self.type_args
        # TODO: The `get` operation in hugr returns an option
        op = UnsupportedOp(
            op_name="prelude.get",
            inputs=[array_ty, idx_ty],
            outputs=[array_ty, elem_ty],
        )
        node = self.builder.add_op(op, array, idx)
        return CallReturnWires(regular_returns=[node[1]], inout_returns=[node[0]])

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
            case.set_outputs(build_panic(case, [], [elem_ty], error))
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
    # TODO: The `set` operation in hugr returns an either
    op = UnsupportedOp(
        op_name="prelude.set",
        inputs=[array_ty, idx_ty, elem_ty],
        outputs=[array_ty, elem_ty],
    )
    array, swapped_elem = iter(builder.add_op(op, array, idx, elem))
    return array, swapped_elem
