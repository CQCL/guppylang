"""Manual instantiation functions for hugr standard operations

We should be able to remove the signature definition redundancies after
https://github.com/CQCL/hugr/issues/1512
"""

from collections.abc import Sequence

import hugr.std.collections
import hugr.std.int
from hugr import ops
from hugr import tys as ht
from hugr.std.int import int_t

from guppylang.tys.arg import TypeArg
from guppylang.tys.ty import OpaqueType, Type


def list_elem_type(ty: Type) -> Type:
    """Returns the guppy element type of a list type."""
    assert isinstance(ty, OpaqueType)
    assert len(ty.args) == 1
    arg = ty.args[0]
    assert isinstance(arg, TypeArg)
    return arg.ty


# --------------------------------------------
# --------------- std.collections ------------
# --------------------------------------------


def _instantiate_list_op(
    name: str, elem_type: ht.Type, inp: list[ht.Type], out: list[ht.Type]
) -> ops.DataflowOp:
    op_def = hugr.std.collections.EXTENSION.get_op(name)
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.TypeTypeArg(elem_type)],
    )


def list_pop(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `pop` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "pop", elem_type, [list_type], [list_type, ht.Option(elem_type)]
    )


def list_push(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `push` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op("push", elem_type, [list_type, elem_type], [list_type])


def list_get(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `get` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "get", elem_type, [list_type, ht.USize()], [ht.Option(elem_type)]
    )


def list_set(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `set` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "set",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [elem_type])],
    )


def list_insert(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `insert` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "insert",
        elem_type,
        [list_type, ht.USize(), elem_type],
        [list_type, ht.Either([elem_type], [ht.Unit])],
    )


def list_length(elem_type: ht.Type) -> ops.DataflowOp:
    """Returns a list `length` operation."""
    list_type = hugr.std.collections.list_type(elem_type)
    return _instantiate_list_op(
        "length",
        elem_type,
        [list_type],
        [list_type, ht.Either([elem_type], [ht.Unit])],
    )


# ------------------------------------------------------
# --------------- std.arithmetic.int -------------------
# ------------------------------------------------------


def _instantiate_int_op(
    name: str,
    int_width: int | Sequence[int],
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.DataflowOp:
    op_def = hugr.std.int.INT_OPS_EXTENSION.get_op(name)
    int_width = [int_width] if isinstance(int_width, int) else int_width
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.BoundedNatArg(w) for w in int_width],
    )


def iwiden_s(from_width: int, to_width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.iwiden_s` operation."""
    return _instantiate_int_op(
        "iwiden_s", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def iwiden_u(from_width: int, to_width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.iwiden_u` operation."""
    return _instantiate_int_op(
        "iwiden_u", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def inarrow_s(from_width: int, to_width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.inarrow_s` operation."""
    return _instantiate_int_op(
        "inarrow_s", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def inarrow_u(from_width: int, to_width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.inarrow_u` operation."""
    return _instantiate_int_op(
        "inarrow_u", [from_width, to_width], [int_t(from_width)], [int_t(to_width)]
    )


def ieq(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ieq` operation."""
    return _instantiate_int_op("ieq", width, [int_t(width), int_t(width)], [ht.Bool])


def ine(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ine` operation."""
    return _instantiate_int_op("ine", width, [int_t(width), int_t(width)], [ht.Bool])


def ilt_u(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ilt_u` operation."""
    return _instantiate_int_op("ilt_u", width, [int_t(width), int_t(width)], [ht.Bool])


def ilt_s(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ilt_s` operation."""
    return _instantiate_int_op("ilt_s", width, [int_t(width), int_t(width)], [ht.Bool])


def igt_u(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.igt_u` operation."""
    return _instantiate_int_op("igt_u", width, [int_t(width), int_t(width)], [ht.Bool])


def igt_s(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.igt_s` operation."""
    return _instantiate_int_op("igt_s", width, [int_t(width), int_t(width)], [ht.Bool])


def ile_u(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ile_u` operation."""
    return _instantiate_int_op("ile_u", width, [int_t(width), int_t(width)], [ht.Bool])


def ile_s(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ile_s` operation."""
    return _instantiate_int_op("ile_s", width, [int_t(width), int_t(width)], [ht.Bool])


def ige_u(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ige_u` operation."""
    return _instantiate_int_op("ige_u", width, [int_t(width), int_t(width)], [ht.Bool])


def ige_s(width: int) -> ops.DataflowOp:
    """Returns a `std.arithmetic.int.ige_s` operation."""
    return _instantiate_int_op("ige_s", width, [int_t(width), int_t(width)], [ht.Bool])


# ------------------------------------------------------
# --------------- std.arithmetic.conversions -----------
# ------------------------------------------------------


def convert_ifromusize() -> ops.DataflowOp:
    """Returns a `std.arithmetic.conversions.ifromusize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifromusize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.USize()], [int_t(6)]),
    )


def convert_itousize() -> ops.DataflowOp:
    """Returns a `std.arithmetic.conversions.itousize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(6)], [ht.USize()]),
    )


def convert_ifrombool() -> ops.DataflowOp:
    """Returns a `std.arithmetic.conversions.ifrombool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifrombool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.Bool], [int_t(1)]),
    )


def convert_itobool() -> ops.DataflowOp:
    """Returns a `std.arithmetic.conversions.itobool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itobool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(1)], [ht.Bool]),
    )
