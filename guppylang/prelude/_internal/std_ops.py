"""Manual instantiation functions for hugr standard operations

We should be able to remove the signature definition redundancies after
https://github.com/CQCL/hugr/issues/1512
"""

from collections.abc import Sequence
from dataclasses import dataclass

import hugr.std.collections
import hugr.std.int
from hugr import ops
from hugr import tys as ht
from hugr import val as hv
from hugr.std.int import int_t

from guppylang.tys.arg import TypeArg
from guppylang.tys.ty import OpaqueType, Type

# --------------------------------------------
# --------------- prelude --------------------
# --------------------------------------------


def array_type(length: int, elem_ty: ht.Type) -> ht.ExtType:
    """Returns the hugr type of a fixed length array."""
    length_arg = ht.BoundedNatArg(length)
    elem_arg = ht.TypeTypeArg(elem_ty)
    return hugr.std.PRELUDE.types["array"].instantiate([length_arg, elem_arg])


def error_type() -> ht.ExtType:
    """Returns the hugr type of an error value."""
    return hugr.std.PRELUDE.types["error"].instantiate([])


def new_array(length: int, elem_ty: ht.Type) -> ops.ExtOp:
    """Returns an operation that creates a new fixed length array."""
    op_def = hugr.std.PRELUDE.get_op("new_array")
    sig = ht.FunctionType([elem_ty] * length, [array_type(length, elem_ty)])
    return ops.ExtOp(op_def, sig, [ht.BoundedNatArg(length), ht.TypeTypeArg(elem_ty)])


@dataclass
class ErrorVal(hv.ExtensionValue):
    """Custom value for a floating point number."""

    signal: int
    message: str

    def to_value(self) -> hv.Extension:
        name = "ConstError"
        payload = {"signal": self.signal, "message": self.message}
        return hv.Extension(
            name, typ=error_type(), val=payload, extensions=[hugr.std.PRELUDE.name]
        )

    def __str__(self) -> str:
        return f"Error({self.signal}): {self.message}"


def panic(inputs: list[ht.Type], outputs: list[ht.Type]) -> ops.ExtOp:
    """Returns an operation that panics."""
    op_def = hugr.std.PRELUDE.get_op("panic")
    args: list[ht.TypeArg] = [
        ht.SequenceArg([ht.TypeTypeArg(ty) for ty in inputs]),
        ht.SequenceArg([ht.TypeTypeArg(ty) for ty in outputs]),
    ]
    sig = ht.FunctionType([error_type(), *inputs], outputs)
    return ops.ExtOp(op_def, sig, args)


# --------------------------------------------
# --------------- std.collections ------------
# --------------------------------------------


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
# --------------- std.arithmetic.int -------------------
# ------------------------------------------------------


def _instantiate_int_op(
    name: str,
    int_width: int | Sequence[int],
    inp: list[ht.Type],
    out: list[ht.Type],
) -> ops.ExtOp:
    op_def = hugr.std.int.INT_OPS_EXTENSION.get_op(name)
    int_width = [int_width] if isinstance(int_width, int) else int_width
    return ops.ExtOp(
        op_def,
        ht.FunctionType(inp, out),
        [ht.BoundedNatArg(w) for w in int_width],
    )


def ieq(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ieq` operation."""
    return _instantiate_int_op("ieq", width, [int_t(width), int_t(width)], [ht.Bool])


def ine(width: int) -> ops.ExtOp:
    """Returns a `std.arithmetic.int.ine` operation."""
    return _instantiate_int_op("ine", width, [int_t(width), int_t(width)], [ht.Bool])


# ------------------------------------------------------
# --------------- std.arithmetic.conversions -----------
# ------------------------------------------------------


def convert_ifromusize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifromusize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifromusize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.USize()], [int_t(6)]),
    )


def convert_itousize() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itousize` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itousize")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(6)], [ht.USize()]),
    )


def convert_ifrombool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.ifrombool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("ifrombool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([ht.Bool], [int_t(1)]),
    )


def convert_itobool() -> ops.ExtOp:
    """Returns a `std.arithmetic.conversions.itobool` operation."""
    op_def = hugr.std.int.CONVERSIONS_EXTENSION.get_op("itobool")
    return ops.ExtOp(
        op_def,
        ht.FunctionType([int_t(1)], [ht.Bool]),
    )
