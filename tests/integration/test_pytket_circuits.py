"""Tests for loading pytket circuits as functions."""

from importlib.util import find_spec

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.quantum import qubit
from guppylang.std.builtins import array

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


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_measure(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)
    circ.measure_all()

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q: qubit) -> bool: ...

    @guppy(module)
    def foo(q: qubit) -> bool:
        return guppy_circ(q)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_measure_multiple(validate):
    from pytket import Circuit

    circ = Circuit(2, 2)
    circ.H(0)
    circ.measure_all()

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit, q2: qubit) -> tuple[bool, bool]: ...

    @guppy(module)
    def foo(q1: qubit, q2: qubit) -> tuple[bool, bool]:
        return guppy_circ(q1, q2)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_measure_not_last(validate):
    from pytket import Circuit

    circ = Circuit(1, 1)
    circ.H(0)
    circ.measure_all()
    circ.X(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q: qubit) -> bool: ...

    @guppy(module)
    def foo(q: qubit) -> bool:
        return guppy_circ(q)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_load_circuit(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module)

    @guppy(module)
    def foo(q: qubit) -> None:
        guppy_circ(q)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_load_circuits(validate):
    from pytket import Circuit

    circ1 = Circuit(1)
    circ1.H(0)

    circ2 = Circuit(2)
    circ2.CX(0, 1)
    circ2.measure_all()

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ1", circ1, module)
    guppy.load_pytket("guppy_circ2", circ2, module)

    @guppy(module)
    def foo(q1: qubit, q2: qubit, q3: qubit) -> tuple[bool, bool]:
        guppy_circ1(q1)
        return  guppy_circ2(q2, q3)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_registers(validate):
    from pytket import Circuit

    circ = Circuit(1)
    q_reg = circ.add_q_register("qubits", 2)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit, reg: array[qubit, 2]) -> None: ...

    @guppy(module)
    def foo(q1: qubit, reg: array[qubit, 2]) -> None:
        guppy_circ(q1, reg)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_registers_measure(validate):
    from pytket import Circuit

    circ = Circuit(1, 1)
    q_reg1 = circ.add_q_register("qubits1", 2)
    q_reg2 = circ.add_q_register("qubits2", 3)
    circ.measure_register(q_reg1, "bits")
    circ.Measure(0, 0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit, 
                   reg1: array[qubit, 2], 
                   reg2: array[qubit, 3]) -> tuple[bool, array[bool, 2]]: ...

    @guppy(module)
    def foo(q1: qubit, reg1: array[qubit, 2], reg2: array[qubit, 3]) -> None:
        guppy_circ(q1, reg1, reg2)

    validate(module.compile())
