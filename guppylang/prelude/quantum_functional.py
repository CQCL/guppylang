"""Guppy standard module for quantum operations."""

# mypy: disable-error-code="empty-body, misc, valid-type"

import typing

from guppylang.decorator import guppy
from guppylang.prelude._internal.compiler.quantum import HSERIES_EXTENSION
from guppylang.prelude._internal.util import quantum_op
from guppylang.prelude.angles import angle
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import quantum, qubit


@guppy.hugr_op(quantum, quantum_op("H"))
def h(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("CZ"))
def cz(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("CX"))
def cx(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("T"))
def t(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("S"))
def s(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("X"))
def x(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Y"))
def y(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Z"))
def z(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Tdg"))
def tdg(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Sdg"))
def sdg(q: qubit @ owned) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("ZZMax", ext=HSERIES_EXTENSION))
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]: ...


@guppy.hugr_op(quantum, quantum_op("Rz"))
def rz(q: qubit @ owned, angle: angle) -> qubit: ...


@guppy.hugr_op(quantum, quantum_op("Rx"))
def rx(q: qubit @ owned, angle: angle) -> qubit: ...


@guppy(quantum)
@typing.no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    f1 = float(angle1)
    f2 = float(angle2)
    return _phased_x(q, f1, f2)


@guppy(quantum)
@typing.no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    f = float(angle)
    return _zz_phase(q1, q2, f)


@guppy.hugr_op(quantum, quantum_op("Reset"))
def reset(q: qubit @ owned) -> qubit: ...


# ------------------------------------------------------
# --------- Internal definitions -----------------------
# ------------------------------------------------------


@guppy.hugr_op(quantum, quantum_op("PhasedX", ext=HSERIES_EXTENSION))
def _phased_x(q: qubit @ owned, angle1: float, angle2: float) -> qubit:
    """PhasedX operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """


@guppy.hugr_op(quantum, quantum_op("ZZPhase", ext=HSERIES_EXTENSION))
def _zz_phase(
    q1: qubit @ owned,
    q2: qubit @ owned,
    angle: float,
) -> tuple[qubit, qubit]:
    """ZZPhase operation from the hseries extension.

    See `guppylang.prelude.quantum.phased_x` for a public definition that
    accepts angle parameters.
    """
