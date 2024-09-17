"""Compilers building list functions on top of hugr standard operations, that involve
multiple nodes.
"""

from __future__ import annotations

import math

from hugr import Wire, ops
from hugr import tys as ht
from hugr.std.float import FLOAT_OPS_EXTENSION, FLOAT_T, FloatVal

from guppylang.definition.custom import CustomInoutCallCompiler, CustomCallCompiler
from guppylang.definition.value import CallReturnWires
from guppylang.prelude._internal.compiler.prelude import build_error, build_panic
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


def from_halfturns() -> ops.ExtOp:
    return ops.ExtOp(
        ROTATION_EXTENSION.get_op("from_halfturns"),
        ht.FunctionType([FLOAT_T], [ht.Sum([[], [ROTATION_T]])]),
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

class RotationCompiler(CustomCallCompiler):
    opname: str

    def __init__(self, opname: str):
        self.opname = opname

    def compile(self, args: list[Wire]) -> list[Wire]:
        from guppylang.prelude._internal.util import quantum_op

        [q, angle] = args
        [radians] = self.builder.add_op(ops.UnpackTuple([FLOAT_T]), angle)
        [pi] = self.builder.load(FloatVal(math.pi))
        op = ops.ExtOp(
            FLOAT_OPS_EXTENSION.get_op("fdiv"),
            ht.FunctionType([FLOAT_T, FLOAT_T], [FLOAT_T]),
            [],
        )
        [halfturns] = self.builder.add_op(op, radians, pi)
        [mb_rotation] = self.builder.add_op(from_halfturns(), halfturns)

        conditional = self.builder.add_conditional(mb_rotation)
        with conditional.add_case(0) as case:
            error = build_error(case, 1, "Non-finite number of half-turns")
            case.set_outputs(build_panic(case, [], [ROTATION_T], error))
        with conditional.add_case(1) as case:
            case.set_outputs(*case.inputs())

        q = self.builder.add_op(
            quantum_op(self.opname)(
                ht.FunctionType([ht.Qubit, ROTATION_T], [ht.Qubit]), []
            ),
            q,
            conditional,
        )
        return [q]
