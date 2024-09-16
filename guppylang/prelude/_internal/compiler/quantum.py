"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

from hugr import Wire
from hugr import tys as ht

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


TKET2_EXTENSIONS = [
    FUTURES_EXTENSION,
    HSERIES_EXTENSION,
    QUANTUM_EXTENSION,
    RESULT_EXTENSION,
]


ANGLE_T = QUANTUM_EXTENSION.get_type("angle")

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
