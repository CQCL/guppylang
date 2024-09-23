"""Guppy standard module for quantum operations."""

from typing import no_type_check

import guppylang.prelude.angles as angles
import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy

# mypy: disable-error-code="empty-body, misc, valid-type"
from guppylang.module import GuppyModule
from guppylang.prelude.angles import angle
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit

quantum_functional = GuppyModule("quantum_functional")

quantum_functional.load(qubit, quantum)
quantum_functional.load_all(angles)


@guppy(quantum_functional)
@no_type_check
def h(q: qubit @ owned) -> qubit:
    quantum.h(q)
    return q


@guppy(quantum_functional)
@no_type_check
def cz(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cz(control, target)
    return control, target


@guppy(quantum_functional)
@no_type_check
def cx(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cx(control, target)
    return control, target


@guppy(quantum_functional)
@no_type_check
def cy(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.cy(control, target)
    return control, target


@guppy(quantum_functional)
@no_type_check
def t(q: qubit @ owned) -> qubit:
    quantum.t(q)
    return q


@guppy(quantum_functional)
@no_type_check
def s(q: qubit @ owned) -> qubit:
    quantum.s(q)
    return q


@guppy(quantum_functional)
@no_type_check
def x(q: qubit @ owned) -> qubit:
    quantum.x(q)
    return q


@guppy(quantum_functional)
@no_type_check
def y(q: qubit @ owned) -> qubit:
    quantum.y(q)
    return q


@guppy(quantum_functional)
@no_type_check
def z(q: qubit @ owned) -> qubit:
    quantum.z(q)
    return q


@guppy(quantum_functional)
@no_type_check
def tdg(q: qubit @ owned) -> qubit:
    quantum.tdg(q)
    return q


@guppy(quantum_functional)
@no_type_check
def sdg(q: qubit @ owned) -> qubit:
    quantum.sdg(q)
    return q


@guppy(quantum_functional)
@no_type_check
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.zz_max(q1, q2)
    return q1, q2


@guppy(quantum_functional)
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    quantum.rz(q, angle)
    return q


@guppy(quantum_functional)
@no_type_check
def rx(q: qubit @ owned, angle: angle) -> qubit:
    quantum.rx(q, angle)
    return q


@guppy(quantum_functional)
@no_type_check
def ry(q: qubit @ owned, angle: angle) -> qubit:
    quantum.ry(q, angle)
    return q


@guppy(quantum_functional)
@no_type_check
def crz(
    control: qubit @ owned, target: qubit @ owned, angle: angle
) -> tuple[qubit, qubit]:
    quantum.crz(control, target, angle)
    return control, target


@guppy(quantum_functional)
@no_type_check
def toffoli(
    control1: qubit @ owned, control2: qubit @ owned, target: qubit @ owned
) -> tuple[qubit, qubit, qubit]:
    quantum.toffoli(control1, control2, target)
    return control1, control2, target


@guppy(quantum_functional)
@no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    quantum.phased_x(q, angle1, angle2)
    return q


@guppy(quantum_functional)
@no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    quantum.zz_phase(q1, q2, angle)
    return q1, q2


@guppy(quantum_functional)
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    quantum.reset(q)
    return q


@guppy(quantum_functional)
@no_type_check
def measure_return(q: qubit @ owned) -> tuple[qubit, bool]:
    b = quantum.measure_return(q)
    return q, b
