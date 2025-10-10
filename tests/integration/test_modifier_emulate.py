import numpy as np
from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang.std.debug import state_result
from guppylang.std.quantum import (
    discard,
    discard_array,
    qubit,
    UnitaryFlags,
    cx,
    v,
    h,
    x,
    s,
    t,
    toffoli,
    sdg,
    ry,
    crz,
)
from guppylang.std.angles import angle

# Dummy variables to suppress Undefined name
# TODO: `ruff` fails when without these, which need to be fixed
dagger = object()
control = object()


@guppy.with_unitary_flags(UnitaryFlags.Unitary)
@guppy
def foo(q1: qubit, q2: qubit, q3: qubit, q4: qubit) -> None:
    h(q1)
    cx(q1, q2)
    v(q1)
    h(q1)
    x(q3)
    with dagger:
        s(q1)
    with control(q2):
        toffoli(q1, q3, q4)
        t(q3)
    sdg(q1)
    ry(q1, angle(0.12))
    crz(q1, q3, angle(0.38))
    h(q1)
    toffoli(q1, q2, q3)
    s(q3)


def test_dagger():
    @guppy
    def dagger_involution() -> None:
        q1 = qubit()
        q2 = qubit()
        q3 = qubit()
        q4 = qubit()

        with dagger:
            foo(q1, q2, q3, q4)
        foo(q1, q2, q3, q4)
        q = array(q1, q2, q3, q4)
        state_result("zero", q)
        discard_array(q)

    shots = dagger_involution.emulator(n_qubits=6).statevector_sim().with_seed(1).run()

    for states in shots.partial_state_dicts():
        state_vector1 = states["zero"].as_single_state()

        diff = np.abs(
            state_vector1 - np.array([1.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        )
        assert np.all(diff < 1e-6), f"State vector non zero: {diff}"


def test_ctrl():
    @guppy
    def test_ctrl() -> None:
        q = array(qubit() for _ in range(4))
        foo(q[0], q[1], q[2], q[3])
        state_result("foo", q)
        discard_array(q)

        q = array(qubit() for _ in range(4))
        c = qubit()
        x(c)
        with control(c):
            foo(q[0], q[1], q[2], q[3])
        state_result("ctrl_foo", q)
        discard_array(q)
        discard(c)

    shots = test_ctrl.emulator(n_qubits=7).statevector_sim().with_seed(1).run()

    for states in shots.partial_state_dicts():
        state_vector1 = states["foo"].as_single_state()
        state_vector2 = states["ctrl_foo"].as_single_state()

        diff = np.abs(state_vector1 - state_vector2)
        assert np.all(diff < 1e-6), f"State vectors are different: {diff}"
