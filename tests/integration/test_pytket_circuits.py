"""Tests for loading pytket circuits as functions."""

from importlib.util import find_spec

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.quantum import qubit

tket2_installed = find_spec("tket2") is not None


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_single_qubit_circuit(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit) -> None: ...

    @guppy(module)
    def foo(q: qubit) -> None:
        guppy_circ(q)

    validate(module.compile())

@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_multi_qubit_circuit(validate):
    from pytket import Circuit

    circ = Circuit(2)
    circ.H(0)
    circ.CX(0, 1)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit, q2: qubit) -> None: ...

    @guppy(module)
    def foo(q1: qubit, q2: qubit) -> None:
        guppy_circ(q1, q2)

    validate(module.compile())