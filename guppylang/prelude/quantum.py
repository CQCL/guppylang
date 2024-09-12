"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc"

import typing

from hugr import tys as ht

from guppylang.decorator import guppy
from guppylang.prelude._internal.compiler.quantum import (
    HSERIES_EXTENSION,
    MeasureCompiler,
    QAllocCompiler,
)
from guppylang.prelude._internal.util import quantum_op
from guppylang.prelude.angles import angle


@guppy.type(ht.Qubit, linear=True)
class qubit:
    @guppy.custom(QAllocCompiler())
    def __new__() -> "qubit": ...


@guppy.hugr_op(quantum_op("QAlloc"))
def dirty_qubit() -> qubit: ...


@guppy.hugr_op(quantum_op("H"))
def h(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("CZ"))
def cz(control: qubit, target: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum_op("CX"))
def cx(control: qubit, target: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum_op("T"))
def t(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("S"))
def s(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("X"))
def x(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("Y"))
def y(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("Z"))
def z(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("Tdg"))
def tdg(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("Sdg"))
def sdg(q: qubit) -> qubit: ...


@guppy.hugr_op(quantum_op("ZZMax", ext=HSERIES_EXTENSION))
def zz_max(q1: qubit, q2: qubit) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum_op("Measure"))
def measure_return(q: qubit) -> tuple[qubit, bool]: ...


@guppy.hugr_op(quantum_op("Rz"))
def rz(q: qubit, angle: angle) -> qubit: ...


@guppy.hugr_op(quantum_op("Rx"))
def rx(q: qubit, angle: angle) -> qubit: ...


@guppy
@typing.no_type_check
def phased_x(q: qubit, angle1: angle, angle2: angle) -> qubit:
    f1 = float(angle1)
    f2 = float(angle2)
    return _phased_x(q, f1, f2)


@guppy
@typing.no_type_check
def zz_phase(q1: qubit, q2: qubit, angle: angle) -> tuple[qubit, qubit]:
    f = float(angle)
    return _zz_phase(q1, q2, f)


@guppy.hugr_op(quantum_op("QFree"))
def discard(q: qubit) -> None: ...


@guppy.hugr_op(quantum_op("Reset"))
def reset(q: qubit) -> qubit: ...


@guppy.custom(MeasureCompiler())
def measure(q: qubit) -> bool: ...


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@guppy.hugr_op(quantum_op("PhasedX", ext=HSERIES_EXTENSION))
def _phased_x(q: qubit, angle1: float, angle2: float) -> qubit:
    """PhasedX operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum_op("ZZPhase", ext=HSERIES_EXTENSION))
def _zz_phase(q1: qubit, q2: qubit, angle: float) -> tuple[qubit, qubit]:
    """ZZPhase operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """
