"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.float import FLOAT_T

from guppylang.definition.custom import CustomCallCompiler
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


def fromturns() -> ops.ExtOp:
    return ops.ExtOp(
        ROTATION_EXTENSION.get_op("fromturns"), ht.FunctionType([FLOAT_T], [ROTATION_T])
    )


# ------------------------------------------------------
# --------- Custom compilers for non-native ops --------
# ------------------------------------------------------


class MeasureCompiler(CustomCallCompiler):
    """Compiler for the `measure` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude._internal.util import quantum_op

        [q] = args
        [q, bit] = self.builder.add_op(
            quantum_op("Measure")(ht.FunctionType([ht.Qubit], [ht.Qubit, ht.Bool]), []),
            q,
        )
        self.builder.add_op(quantum_op("QFree")(ht.FunctionType([ht.Qubit], []), []), q)
        return [bit]


class QAllocCompiler(CustomCallCompiler):
    """Compiler for the `qubit` function."""

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude._internal.util import quantum_op

        assert not args, "qubit() does not take any arguments"
        q = self.builder.add_op(
            quantum_op("QAlloc")(ht.FunctionType([], [ht.Qubit]), [])
        )
        q = self.builder.add_op(
            quantum_op("Reset")(ht.FunctionType([ht.Qubit], [ht.Qubit]), []), q
        )
        return [q]


class RotationCompiler(CustomCallCompiler):
    opname: str

    def __init__(self, opname: str):
        self.opname = opname

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude._internal.util import quantum_op

        [q, angle] = args
        [halfturns] = self.builder.add_op(ops.UnpackTuple([FLOAT_T]), angle)
        [rot] = self.builder.add_op(fromturns(), halfturns)
        q = self.builder.add_op(
            quantum_op(self.opname)(
                ht.FunctionType([ht.Qubit, ROTATION_T], [ht.Qubit]), []
            ),
            q,
            rot,
        )
        return [q]
