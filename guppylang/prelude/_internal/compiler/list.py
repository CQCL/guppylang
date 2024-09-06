"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import hugr.std.collections
from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.collections import ListVal

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase


# ------------------------------------------------------
# --------- std.collections operations -----------------
# ------------------------------------------------------


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


def list_new(
    builder: DfBase[ops.DfParentOp], elem_type: ht.Type, args: list[Wire]
) -> list[Wire]:
    # This may be simplified in the future with a `new` or `with_capacity` list op
    # See https://github.com/CQCL/hugr/issues/1508
    lst = builder.load(ListVal([], elem_ty=elem_type))
    push_op = list_push(elem_type)
    for elem in args:
        lst = builder.add_op(push_op, lst, elem)
    return [lst]
