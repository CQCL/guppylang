"""Various tests for the functions defined in `guppylang.prelude.quantum`."""

from typing import no_type_check
from hugr.package import ModulePointer

import guppylang.decorator
from guppylang.module import GuppyModule
from guppylang.std.angles import angle

from guppylang.std.builtins import owned, array

from guppylang.std.quantum import (
    discard,
    measure,
    qubit,
    maybe_qubit,
    measure_array,
    discard_array,
)
from guppylang.std.quantum_functional import (
    cx,
    cy,
    cz,
    h,
    t,
    s,
    x,
    y,
    z,
    tdg,
    sdg,
    rx,
    ry,
    rz,
    crz,
    toffoli,
    reset,
    quantum_functional,
    project_z,
)


def compile_quantum_guppy(fn) -> ModulePointer:
    """A decorator that combines @guppy with HUGR compilation.

    Modified version of `tests.util.compile_guppy` that loads the quantum module.
    """
    assert not isinstance(
        fn,
        GuppyModule,
    ), "`@compile_quantum_guppy` does not support extra arguments."

    module = GuppyModule("module")
    module.load(
        angle, qubit, discard, measure, measure_array, maybe_qubit, discard_array
    )
    module.load_all(quantum_functional)
    guppylang.decorator.guppy(module)(fn)
    return module.compile()


def test_alloc(validate):
    @compile_quantum_guppy
    def test() -> tuple[bool, bool]:
        q1, q2 = qubit(), maybe_qubit().unwrap()
        q1, q2 = cx(q1, q2)
        return (measure(q1), measure(q2))

    validate(test)


def test_1qb_op(validate):
    @compile_quantum_guppy
    def test(q: qubit @ owned) -> qubit:
        q = h(q)
        q = t(q)
        q = s(q)
        q = x(q)
        q = y(q)
        q = z(q)
        q = tdg(q)
        q = sdg(q)
        return q

    validate(test)


def test_2qb_op(validate):
    @compile_quantum_guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[qubit, qubit]:
        q1, q2 = cx(q1, q2)
        q1, q2 = cy(q1, q2)
        q1, q2 = cz(q1, q2)
        return (q1, q2)

    validate(test)


def test_3qb_op(validate):
    @compile_quantum_guppy
    def test(
        q1: qubit @ owned, q2: qubit @ owned, q3: qubit @ owned
    ) -> tuple[qubit, qubit, qubit]:
        q1, q2, q3 = toffoli(q1, q2, q3)
        return (q1, q2, q3)

    validate(test)


def test_measure_ops(validate):
    """Compile various measurement-related operations."""

    @compile_quantum_guppy
    def test(q1: qubit @ owned, q2: qubit @ owned) -> tuple[bool, bool]:
        q1, b1 = project_z(q1)
        q1 = discard(q1)
        q2 = reset(q2)
        b2 = measure(q2)
        return (b1, b2)

    validate(test)


def test_parametric(validate):
    """Compile various parametric operations."""

    @compile_quantum_guppy
    def test(
        q1: qubit @ owned, q2: qubit @ owned, a1: angle, a2: angle, a3: angle
    ) -> tuple[qubit, qubit]:
        q1 = rx(q1, a1)
        q1 = ry(q1, a1)
        q2 = rz(q2, a3)
        q1, q2 = crz(q1, q2, a3)
        return (q1, q2)


def test_measure_array(validate):
    """Build and measure array."""

    @compile_quantum_guppy
    def test() -> array[bool, 10]:
        qs = array(qubit() for _ in range(10))
        return measure_array(qs)

    validate(test)


def test_discard_array(validate):
    """Build and discard array."""

    @compile_quantum_guppy
    def test() -> None:
        qs = array(qubit() for _ in range(10))
        discard_array(qs)

    validate(test)


def test_panic_discard(validate):
    """Panic while discarding qubit."""

    @compile_quantum_guppy
    @no_type_check
    def test() -> None:
        q = qubit()
        panic("I panicked!", q)

    validate(test)
