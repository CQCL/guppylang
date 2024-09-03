"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING

import hugr.std.int
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections import ListVal

from guppylang.definition.custom import CustomCallCompiler
from guppylang.error import InternalGuppyError
from guppylang.prelude._internal.std_ops import (
    convert_ifromusize,
    ieq,
    ine,
    list_length,
    list_pop,
    list_push,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from hugr.build.dfg import DfBase


@dataclass
class ListOpCompiler(CustomCallCompiler, ABC):
    """Generic compiler for list operations that involve multiple nodes.

    args:
        builder: The function builder where the function should be defined.
        type_args: The type arguments for the function.
        globals: The compiled globals.
        node: The AST node where the function is defined.
        ty: The type of the function, if known.
        fn: The builder function to use. See `guppylang.prelude._internal.list_compiler`
        elem_type: The type of the elements in the list. If None, the compiler must
            only be used with non-empty lists.
    """

    fn: Callable[[DfBase[ops.DfParentOp], ht.Type | None, list[Wire]], list[Wire]]
    elem_type: ht.Type | None = None

    def compile(self, args: list[Wire]) -> list[Wire]:
        return self.fn(self.builder, self.elem_type, args)


def _get_elem_type(
    builder: DfBase[ops.DfParentOp],
    elem_type: ht.Type | None,
    *,
    lst: Wire | None = None,
    elem: Wire | None = None,
) -> ht.Type:
    """Returns the element type of the list, extracted either from the preset
    `elem_type`, from a list wire, or from an element wire.
    """
    if elem_type is not None:
        return elem_type
    if elem is not None:
        builder.hugr.port_type(elem.out_port())
    if lst is not None:
        list_t = builder.hugr.port_type(lst.out_port())
        assert isinstance(list_t, ht.ExtType)
        arg = list_t.args[0]
        assert isinstance(arg, ht.TypeTypeArg)
        return arg.ty
    raise InternalGuppyError("Could not get the element type")


def list_new(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type | None, args: list[Wire]
) -> list[Wire]:
    # This may be simplified in the future
    # See https://github.com/CQCL/hugr/issues/1508
    ty = _get_elem_type(builder, elem_type, elem=args[0] if args else None)
    lst = builder.load(ListVal([], elem_ty=ty))
    push_op = list_push(ty)
    for elem in args:
        lst = builder.add_op(push_op, lst, elem)
    return [lst]


def list_isEmpty(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type | None, args: list[Wire]
) -> list[Wire]:
    (lst,) = args
    ty = _get_elem_type(builder, elem_type, lst=lst)
    length = builder.add_op(list_length(ty), lst)
    length = builder.add_op(convert_ifromusize(), length)
    zero = builder.load(hugr.std.int.IntVal(0, width=6))
    is_empty = builder.add_op(ieq(6), length, zero)
    return [lst, is_empty]


def list_isNotEmpty(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type | None, args: list[Wire]
) -> list[Wire]:
    (lst,) = args
    ty = _get_elem_type(builder, elem_type, lst=lst)
    length = builder.add_op(list_length(ty), lst)
    length = builder.add_op(convert_ifromusize(), length)
    zero = builder.load(hugr.std.int.IntVal(0, width=6))
    is_empty = builder.add_op(ine(6), length, zero)
    return [is_empty, lst]


def list_append(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type | None, args: list[Wire]
) -> list[Wire]:
    (list1, list2) = args
    ty = _get_elem_type(builder, elem_type, lst=list1)

    # It'd be nice to preallocate `len(list2)` capacity on list1 here,
    # if that gets added in
    # https://github.com/CQCL/hugr/issues/1508
    with builder.add_tail_loop([], [list1, list2]) as loop:
        list1, list2 = loop.inputs()
        list2, elem = loop.add_op(list_pop(ty), list2).outputs()

        # The returned `elem` is an option.
        # If it has a value, we append it to the list and continue with the loop.
        # Otherwise, it means the second list is empty, so we return the first list.

        # TODO

        # Output the branch predicate and the inputs for the next iteration
        # loop.set_loop_outputs(sum_wire=elem_is_none, list1, list2)

    list1, list2 = loop.outputs()

    # Discard the empty list2
    # TODO

    return [list1]


def dummy_op(
    name: str,
) -> Callable[[DfBase[ops.DfParentOp], ht.Type | None, list[Wire]], list[Wire]]:
    """Dummy operation, used as a placeholder for missing list operations."""

    def compile(
        builder: DfBase[ops.DfParentOp], elem_type: ht.Type | None, args: list[Wire]
    ) -> list[Wire]:
        raise InternalGuppyError(f"List operation not implemented for {name}")

    return compile
