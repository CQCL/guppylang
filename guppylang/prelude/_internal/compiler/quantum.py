"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from hugr import Wire
from hugr import tys as ht

from guppylang.definition.custom import CustomCallCompiler
from guppylang.prelude._internal.json_defs import load_extension

# ----------------------------------------------
# --------- tket2.* extensions -----------------
# ----------------------------------------------

FUTURES_EXTENSION = load_extension("tket2.futures")
HSERIES_EXTENSION = load_extension("tket2.hseries")
QUANTUM_EXTENSION = load_extension("tket2.quantum")
RESULT_EXTENSION = load_extension("tket2.result")
ANGLE_EXTENSION = load_extension("tket2.angle")

TKET2_EXTENSIONS = [
    FUTURES_EXTENSION,
    HSERIES_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
    ANGLE_EXTENSION,
]


ANGLE_T_DEF = ANGLE_EXTENSION.get_type("angle")
ANGLE_T = ht.ExtType(ANGLE_T_DEF)
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
