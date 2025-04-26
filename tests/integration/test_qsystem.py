from hugr.package import ModulePointer

import guppylang.decorator
from guppylang.module import GuppyModule
from guppylang.std.angles import angle

from guppylang.std.builtins import owned, array
from guppylang.std.qsystem.random import RNG
from guppylang.std.qsystem.utils import get_current_shot
from guppylang.std.quantum import qubit, measure_array
from guppylang.std.qsystem.functional import (
    phased_x,
    zz_phase,
    qsystem_functional,
    measure_and_reset,
    zz_max,
    reset,
    rz,
    measure,
    qfree,
)


def compile_qsystem_guppy(fn) -> ModulePointer:  # type: ignore[no-untyped-def]
    """A decorator that combines @guppy with HUGR compilation.

    Modified version of `tests.util.compile_guppy` that loads the qsytem module.
    """
    assert not isinstance(
        fn,
        GuppyModule,
    ), "`@compile_qsystem_guppy` does not support extra arguments."

    module = GuppyModule("module")
    module.load(angle, qubit, get_current_shot, RNG, measure_array)  # type: ignore[arg-type]
    module.load_all(qsystem_functional)
    guppylang.decorator.guppy(module)(fn)
    return module.compile()


def test_qsystem(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem extension."""

    @compile_qsystem_guppy
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

    validate(test)


def test_qsystem_random(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem random extension."""

    @compile_qsystem_guppy
    def test() -> tuple[int, float, int]:
        rng = RNG(42)
        rint = rng.random_int()
        rfloat = rng.random_float()
        rint_bnd = rng.random_int_bounded(100)
        ar = array(qubit() for _ in range(5))
        rng.shuffle(ar)
        _ = measure_array(ar)
        rng.discard()

        return rint, rfloat, rint_bnd

    validate(test)
