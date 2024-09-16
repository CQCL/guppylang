"""Compilers building array functions on top of hugr standard operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import hugr.std.collections
import hugr.std.int
from hugr import Node, Wire, ops
from hugr import tys as ht
from hugr import val as hv

if TYPE_CHECKING:
    from hugr.build.dfg import DfBase

# --------------------------------------------
# --------------- prelude --------------------
# --------------------------------------------


def error_type() -> ht.ExtType:
    """Returns the hugr type of an error value."""
    return hugr.std.PRELUDE.types["error"].instantiate([])


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


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


def build_panic(
    builder: DfBase[ops.Case],
    in_tys: ht.TypeRow,
    out_tys: ht.TypeRow,
    err: Wire,
    *args: Wire,
) -> Node:
    """Builds a panic operation."""
    op = panic(in_tys, out_tys)
    return builder.add_op(op, err, *args)


def build_error(builder: DfBase[ops.Case], signal: int, msg: str) -> Wire:
    """Constructs and loads a static error value."""
    val = ErrorVal(signal, msg)
    return builder.load(builder.add_const(val))
