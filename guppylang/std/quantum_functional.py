"""Guppy standard module for quantum operations."""

from typing import no_type_check

import guppylang.std.angles as angles
import guppylang.std.quantum as quantum
from guppylang.decorator import guppy

# mypy: disable-error-code="empty-body, misc, valid-type"
from guppylang.module import GuppyModule
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

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
def reset(q: qubit @ owned) -> qubit:
    quantum.reset(q)
    return q


@guppy(quantum_functional)
@no_type_check
def project_z(q: qubit @ owned) -> tuple[qubit, bool]:
    b = quantum.project_z(q)
    return q, b


# -------NON-PRIMITIVE-------


@guppy(quantum_functional)
@no_type_check
def ch(control: qubit @ owned, target: qubit @ owned) -> tuple[qubit, qubit]:
    quantum.ch(control, target)
    return control, target
