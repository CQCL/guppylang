"""Tests for lowering guppy definitions to pytket circuits.

As pytket does not have the same expressivity as HUGR, this test suite only
includes programs that we know should be lowerable.

This depends on the lowering passes implemented by `tket2`. If guppy generated
HUGRs change their structure in a way that is no longer supported by those
passes, disable the failing tests and open an issue to improve support in tket2.

https://github.com/CQCL/tket2/issues/new
"""

from importlib.util import find_spec

import math
import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.angles import pi
from guppylang.prelude.builtins import owned, py
from guppylang.prelude.quantum import measure, qubit, quantum
from guppylang.prelude.quantum_functional import phased_x, rz, zz_max
from tests.util import guppy_to_circuit

tket2_installed = find_spec("tket2") is not None


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_lower_pure_circuit():
    import pytket

    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(pi, phased_x, rz, zz_max)

    @guppy(module)
    def my_func(
        q0: qubit @owned,
        q1: qubit @owned,
    ) -> tuple[qubit, qubit]:
        q0 = phased_x(q0, pi / 2, pi / 2)
        q0 = rz(q0, pi)
        q1 = phased_x(q1, pi / 2, -pi / 2)
        q1 = rz(q1, pi)
        q0, q1 = zz_max(q0, q1)
        q0 = rz(q0, pi)
        q1 = rz(q1, pi)
        return (q0, q1)

    circ = guppy_to_circuit(my_func)

    tk1 = circ.to_tket1()
    assert tk1.n_qubits == 2
    # TODO: The tket1 conversion needs to be updated with all the hugr ops changes
    # before we can test the translated ops
    # ops = {g.op.type for g in tk1}
    # assert pytket.circuit.OpType.ZZMax in ops


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_lower_hybrid_circuit():
    import pytket

    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(pi, phased_x, rz, zz_max)

    @guppy(module)
    def my_func(
        q0: qubit @owned,
        q1: qubit @owned,
    ) -> tuple[bool,]:
        q0 = phased_x(q0, pi / 2, pi / 2)
        q0 = rz(q0, pi)
        q1 = phased_x(q1, pi / 2, -pi / 2)
        q1 = rz(q1, pi)
        q0, q1 = zz_max(q0, q1)
        _ = measure(q0)
        return (measure(q1),)

    circ = guppy_to_circuit(my_func)

    tk1 = circ.to_tket1()
    assert tk1.n_qubits == 2
    # TODO: The tket1 conversion needs to be updated with all the hugr ops changes
    # before we can test the translated ops
    # ops = {g.op.type for g in tk1}
    # assert pytket.circuit.OpType.ZZMax in ops
