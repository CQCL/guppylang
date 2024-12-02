from typing import no_type_check

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import angles, qsystem
from guppylang.std.angles import angle
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

qsystem_functional = GuppyModule("qsystem_functional")

qsystem_functional.load(qubit, qsystem)
qsystem_functional.load_all(angles)


@guppy(qsystem_functional)
@no_type_check
def phased_x(q: qubit @ owned, angle1: angle, angle2: angle) -> qubit:
    qsystem.phased_x(q, angle1, angle2)
    return q


@guppy(qsystem_functional)
@no_type_check
def zz_phase(q1: qubit @ owned, q2: qubit @ owned, angle: angle) -> tuple[qubit, qubit]:
    qsystem.zz_phase(q1, q2, angle)
    return q1, q2


@guppy(qsystem_functional)
@no_type_check
def measure_and_reset(q: qubit @ owned) -> tuple[qubit, bool]:
    b = qsystem.measure_and_reset(q)
    return q, b


@guppy(qsystem_functional)
@no_type_check
def zz_max(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
    qsystem.zz_max(q1, q2)
    return q1, q2


@guppy(qsystem_functional)
@no_type_check
def rz(q: qubit @ owned, angle: angle) -> qubit:
    qsystem.rz(q, angle)
    return q


@guppy(qsystem_functional)
@no_type_check
def measure(q: qubit @ owned) -> bool:
    result = qsystem.measure(q)
    return result


@guppy(qsystem_functional)
@no_type_check
def qfree(q: qubit @ owned) -> None:
    qsystem.qfree(q)


@guppy(qsystem_functional)
@no_type_check
def reset(q: qubit @ owned) -> qubit:
    qsystem.reset(q)
    return q
