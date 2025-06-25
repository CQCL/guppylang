from hugr.package import ModulePointer

from guppylang.decorator import guppy
from guppylang.std.angles import angle
from guppylang.std.builtins import owned, array
from guppylang.std.qsystem.random import make_discrete_distribution, RNG

from guppylang.std.qsystem.utils import get_current_shot
from guppylang.std.quantum import qubit, measure_array
from guppylang.std.qsystem.functional import (
    phased_x,
    zz_phase,
    measure_and_reset,
    zz_max,
    reset,
    rz,
    measure,
    qfree,
)
from tests.util import compile_guppy


def test_qsystem(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem extension."""

    @guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, a1: angle) -> bool:
        shot = get_current_shot()
        q1 = phased_x(q1, a1, a1)
        q1, q2 = zz_phase(q1, q2, a1)
        q1 = rz(q1, a1)
        q1, q2 = zz_max(q1, q2)
        q1, b = measure_and_reset(q1)
        q1 = reset(q1)
        b = measure(q1)
        qfree(q2)
        return b

    validate(guppy.compile(test))


def test_qsystem_random(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem random extension."""

    @guppy
    def test() -> tuple[int, float, int, int, angle, angle]:
        rng = RNG(42)
        rint = rng.random_int()
        rfloat = rng.random_float()
        rint_bnd = rng.random_int_bounded(100)
        ar = array(qubit() for _ in range(5))
        rng.shuffle(ar)
        _ = measure_array(ar)
        dist = make_discrete_distribution(array(0.0, 1.0, 2.0, 3.0))
        rint_discrete = dist.sample(rng)
        rangle = rng.random_angle()
        rcangle = rng.random_clifford_angle()
        rng.discard()

        return rint, rfloat, rint_bnd, rint_discrete, rangle, rcangle

    validate(guppy.compile(test))

def test_measure_leaked(validate):  # type: ignore[no-untyped-def]
    """Compile the measure_leaked operation."""

    @guppy
    def test(q: qubit @ owned) -> bool:
        q = qubit()
        m = measure_leaked(q)
        return m

    validate(guppy.compile(test))
