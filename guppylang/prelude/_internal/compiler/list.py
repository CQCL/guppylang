"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import hugr.std.collections
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections import ListVal

from guppylang.error import InternalGuppyError
from guppylang.tys.arg import TypeArg
from guppylang.tys.ty import OpaqueType, Type

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase


# ------------------------------------------------------
# --------- std.collections operations -----------------
# ------------------------------------------------------


def list_elem_type(ty: Type) -> Type:
    """Returns the guppy element type of a list type."""
    assert isinstance(ty, OpaqueType)
    assert len(ty.args) == 1
    arg = ty.args[0]
    assert isinstance(arg, TypeArg)
    return arg.ty


def _instantiate_list_op(
    name: str, elem_type: ht.Type, inp: list[ht.Type], out: list[ht.Type]
) -> ops.ExtOp:
    op_def = hugr.std.collections.EXTENSION.get_op(name)
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.TypeTypeArg(elem_type)],
    )


def list_pop(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `pop` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "pop", elem_type, [list_type], [list_type, ht.Option(elem_type)]
    )


def list_push(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `push` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op("push", elem_type, [list_type, elem_type], [list_type])


def list_get(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `get` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "get", elem_type, [list_type, ht.USize()], [ht.Option(elem_type)]
    )


def list_set(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `set` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "set",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [elem_type])],
    )


def list_insert(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `insert` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "insert",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [ht.Unit])],
    )


def list_length(elem_type: ht.Type) -> ops.ExtOp:
    """Returns a list `length` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "length",
        elem_type,
        [list_type],
        [list_type, ht.Either([elem_type], [ht.Unit])],
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


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
