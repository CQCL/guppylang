"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.float import FLOAT_T

from guppylang.definition.custom import CustomInoutCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.prelude._internal.json_defs import load_extension

# ----------------------------------------------
# --------- tket2.* extensions -----------------
# ----------------------------------------------

FUTURES_EXTENSION = load_extension("tket2.futures")
HSERIES_EXTENSION = load_extension("tket2.hseries")
QUANTUM_EXTENSION = load_extension("tket2.quantum")
RESULT_EXTENSION = load_extension("tket2.result")
ROTATION_EXTENSION = load_extension("tket2.rotation")

ROTATION_T_DEF = ROTATION_EXTENSION.get_type("rotation")
ROTATION_T = ht.ExtType(ROTATION_T_DEF)

TKET2_EXTENSIONS = [
    FUTURES_EXTENSION,
    HSERIES_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
    ROTATION_EXTENSION,
]


def from_halfturns_unchecked() -> ops.ExtOp:
    return ops.ExtOp(
        ROTATION_EXTENSION.get_op("from_halfturns_unchecked"),
        ht.FunctionType([FLOAT_T], [ROTATION_T]),
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class MeasureReturnCompiler(CustomInoutCallCompiler):
    """Compiler for the `measure_return` function."""

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        from guppylang.prelude._internal.util import quantum_op

        [q] = args
        [q, bit] = self.builder.add_op(
            quantum_op("Measure")(ht.FunctionType([ht.Qubit], [ht.Qubit, ht.Bool]), []),
            q,
        )
        return CallReturnWires(regular_returns=[bit], inout_returns=[q])


class RotationCompiler(CustomInoutCallCompiler):
    opname: str

    def __init__(self, opname: str):
        self.opname = opname

    def compile_with_inouts(self, args: list[Wire]) -> CallReturnWires:
        from guppylang.prelude._internal.util import quantum_op

        [*qs, angle] = args
        [halfturns] = self.builder.add_op(ops.UnpackTuple([FLOAT_T]), angle)
        [rotation] = self.builder.add_op(from_halfturns_unchecked(), halfturns)

        qs = self.builder.add_op(
            quantum_op(self.opname)(
                ht.FunctionType(
                    [ht.Qubit for _ in qs] + [ROTATION_T], [ht.Qubit for _ in qs]
                ),
                [],
            ),
            *qs,
            rotation,
        )
        return CallReturnWires(regular_returns=[], inout_returns=list(qs))
