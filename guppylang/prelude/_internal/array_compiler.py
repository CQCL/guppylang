"""Compilers building array functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING

from hugr import Wire, ops
from hugr import tys as ht

from guppylang.definition.custom import CustomCallCompiler
from guppylang.error import InternalGuppyError

if TYPE_CHECKING:
    from collections.abc import Callable

    from hugr.build.dfg import DfBase


@dataclass
class ArrayOpCompiler(CustomCallCompiler, ABC):
    """Generic compiler for array operations that involve multiple nodes.

    args:
        builder: The function builder where the function should be defined.
        type_args: The type arguments for the function.
        globals: The compiled globals.
        node: The AST node where the function is defined.
        ty: The type of the function, if known.
        fn: The builder function to use. See `guppylang.prelude._internal.list_compiler`
        length: The length of the array.
        elem_type: The type of the elements in the list. If None, the compiler must
            only be used with non-empty lists.
    """

    fn: Callable[
        [DfBase[ops.DfParentOp], int | None, ht.Type | None, list[Wire]], list[Wire]
    ]
    length: int | None = None
    elem_type: ht.Type | None = None

    def compile(self, args: list[Wire]) -> list[Wire]:
        return self.fn(self.builder, self.length, self.elem_type, args)


def _get_elem_type(
    builder: DfBase[ops.DfParentOp],
    elem_type: ht.Type | None,
    *,
    arr: Wire | None = None,
    elem: Wire | None = None,
) -> ht.Type:
    """Returns the element type of the array, extracted either from the preset
    `elem_type`, from an array wire, or from an element wire.
    """
    if elem_type is not None:
        return elem_type
    if elem is not None:
        builder.hugr.port_type(elem.out_port())
    if arr is not None:
        list_t = builder.hugr.port_type(arr.out_port())
        assert isinstance(list_t, ht.ExtType)
        arg = list_t.args[1]
        assert isinstance(arg, ht.TypeTypeArg)
        return arg.ty
    raise InternalGuppyError("Could not get the element type")


def _get_arr_length(
    builder: DfBase[ops.DfParentOp],
    length: int | None,
    *,
    arr: Wire | None = None,
) -> int:
    """Returns the length of the array, extracted either from the preset
    `elem_type`, or from an array wire
    """
    if length is not None:
        return length
    if arr is not None:
        list_t = builder.hugr.port_type(arr.out_port())
        assert isinstance(list_t, ht.ExtType)
        arg = list_t.args[0]
        assert isinstance(arg, ht.BoundedNatArg)
        return arg.n
    raise InternalGuppyError("Could not get the array length of the input")
