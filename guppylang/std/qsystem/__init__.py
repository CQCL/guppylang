from typing import no_type_check

from typing_extensions import deprecated

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import angles
from guppylang.std._internal.compiler.quantum import (
    QSYSTEM_EXTENSION,
    InoutMeasureCompiler,
)
from guppylang.std._internal.util import quantum_op
from guppylang.std.angles import angle, pi
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

qsystem = GuppyModule("qsystem")

qsystem.load(qubit)
qsystem.load_all(angles)


@guppy(qsystem)
@no_type_check
def phased_x(q: qubit, angle1: angle, angle2: angle) -> None:
    f1 = float(angle1)
    f2 = float(angle2)
    _phased_x(q, f1, f2)


@guppy(qsystem)
@deprecated("zz_max is not a system primitive, use zz_phase directly with angle pi/2.")
@no_type_check
def zz_max(q1: qubit, q2: qubit) -> None:
    """ZZMax operation from the qsystem extension.

    This is a special case of the ZZPhase operation with angle = pi/2.
    """
    zz_phase(q1, q2, pi / 2)


@guppy(qsystem)
@no_type_check
def zz_phase(q1: qubit, q2: qubit, angle: angle) -> None:
    f = float(angle)
    _zz_phase(q1, q2, f)


@guppy(qsystem)
@no_type_check
def rz(q: qubit, angle: angle) -> None:
    f1 = float(angle)
    _rz(q, f1)


@guppy.hugr_op(quantum_op("Measure", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def measure(q: qubit @ owned) -> bool: ...


@guppy.custom(InoutMeasureCompiler("MeasureReset", QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def measure_and_reset(q: qubit) -> bool:
    """MeasureReset operation from the qsystem extension."""


@guppy.hugr_op(quantum_op("Reset", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def reset(q: qubit) -> None: ...


# TODO
# @guppy.hugr_op(quantum_op("TryQAlloc", ext=QSYSTEM_EXTENSION), module=qsystem)
# @no_type_check
# def _try_qalloc() -> Option[qubit]:
#     ..


@guppy.hugr_op(quantum_op("QFree", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def qfree(q: qubit @ owned) -> None: ...


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@guppy.hugr_op(quantum_op("PhasedX", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _phased_x(q: qubit, angle1: float, angle2: float) -> None:
    """PhasedX operation from the qsystem extension.

    See `guppylang.std.qsystem.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("ZZPhase", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> None:
    """ZZPhase operation from the qsystem extension.

    See `guppylang.std.qsystem.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("Rz", ext=QSYSTEM_EXTENSION), module=qsystem)
@no_type_check
def _rz(q: qubit, angle: float) -> None:
    """Rz operation from the qsystem extension.

    See `guppylang.std.qsystem.rz` for a public definition that
    accepts angle parameters.
    """
