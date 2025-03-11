from hugr.package import ModulePointer

import guppylang.decorator
from guppylang.module import GuppyModule
from guppylang.std.angles import angle

from guppylang.std.builtins import array, nat, owned
from guppylang.std.qsystem.random import RNG, maybe_rng, qsystem_random
from guppylang.std.qsystem.utils import get_current_shot, qsystem_utils, rpc
from guppylang.std.quantum import qubit
from guppylang.std.qsystem.functional import (
    measure_and_reset,
    measure,
    phased_x,
    qfree,
    qsystem_functional,
    reset,
    rz,
    zz_max,
    zz_phase,
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
    module.load(angle, qubit)  # type: ignore[arg-type]
    module.load_all(qsystem_functional)
    module.load_all(qsystem_random)
    module.load_all(qsystem_utils)
    guppylang.decorator.guppy(module)(fn)
    return module.compile()


def test_qsystem(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem extension."""

    @compile_qsystem_guppy
    def test(q1: qubit @ owned, q2: qubit @ owned, a1: angle) -> bool:
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


def test_qsystem_utils(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem utils extension."""

    @compile_qsystem_guppy
    def test() -> array[int, 50]:
        shot = get_current_shot()
        request = array(shot + i for i in range(50))
        response: array[int, 50] = rpc(request)
        return response

    validate(test)


def test_qsystem_random(validate):  # type: ignore[no-untyped-def]
    """Compile various operations from the qsystem random extension."""

    @compile_qsystem_guppy
    def test() -> tuple[int, nat, float, int]:
        rng = RNG(42)
        rng2 = maybe_rng(84)
        rng2.unwrap_nothing()
        rint = rng.random_int()
        rnat = rng.random_nat()
        rfloat = rng.random_float()
        rint_bnd = rng.random_int_bounded(100)
        rng.discard()
        return rint, rnat, rfloat, rint_bnd

    validate(test)
