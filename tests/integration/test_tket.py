"""Tests for lowering guppy definitions to pytket circuits.

As pytket does not have the same expressivity as HUGR, this test suite only
includes programs that we know should be lowerable.

This depends on the lowering passes implemented by `tket2`. If guppy generated
HUGRs change their structure in a way that is no longer supported by those
passes, disable the failing tests and open an issue to improve support in tket2.

https://github.com/CQCL/tket2/issues/new
"""

from importlib.util import find_spec
from typing import no_type_check

import math
import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import py
from guppylang.prelude.quantum import qubit, quantum
from guppylang.prelude.quantum import measure, phased_x, rz, zz_max
from tests.util import guppy_to_circuit

tket2_installed = find_spec("tket2") is not None


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_lower_pure_circuit():
    import pytket

    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    @no_type_check
    def my_func(
        q0: qubit,
        q1: qubit,
    ) -> tuple[qubit, qubit]:  # pragma: no cover
        q0 = phased_x(q0, py(math.pi / 2), py(-math.pi / 2))
        q0 = rz(q0, py(math.pi))
        q1 = phased_x(q1, py(math.pi / 2), py(-math.pi / 2))
        q1 = rz(q1, py(math.pi))
        q0, q1 = zz_max(q0, q1)
        q0 = rz(q0, py(math.pi))
        q1 = rz(q1, py(math.pi))
        return (q0, q1)

    circ = guppy_to_circuit(my_func)
    assert circ.num_operations() == 7

    tk1 = circ.to_tket1()
    assert tk1.n_gates == 7
    assert tk1.n_qubits == 2

    gates = list(tk1)
    assert gates[4].op.type == pytket.circuit.OpType.ZZMax


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_lower_hybrid_circuit():
    import pytket

    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    @no_type_check
    def my_func(
        q0: qubit,
        q1: qubit,
    ) -> tuple[bool,]:  # pragma: no cover
        q0 = phased_x(q0, py(math.pi / 2), py(-math.pi / 2))
        q0 = rz(q0, py(math.pi))
        q1 = phased_x(q1, py(math.pi / 2), py(-math.pi / 2))
        q1 = rz(q1, py(math.pi))
        q0, q1 = zz_max(q0, q1)
        _ = measure(q0)
        return (measure(q1),)

    circ = guppy_to_circuit(my_func)

    # The 7 operations in the function, plus two implicit QFree
    assert circ.num_operations() == 9

    tk1 = circ.to_tket1()
    assert tk1.n_gates == 7
    assert tk1.n_qubits == 2

    gates = list(tk1)
    assert gates[4].op.type == pytket.circuit.OpType.ZZMax
