"""Tests for loading pytket circuits as functions."""

from importlib.util import find_spec

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.quantum import qubit, discard_array
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

    guppy.load_pytket("guppy_circ", circ, module, use_arrays=False)

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

    guppy.load_pytket("guppy_circ1", circ1, module, use_arrays=False)
    guppy.load_pytket("guppy_circ2", circ2, module, use_arrays=False)

    @guppy(module)
    def foo(q1: qubit, q2: qubit, q3: qubit) -> tuple[bool, bool]:
        guppy_circ1(q1)
        return  guppy_circ2(q2, q3)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_measure_some(validate):
    from pytket import Circuit

    circ = Circuit(2, 1)
    circ.CX(0, 1)
    circ.Measure(0, 0)

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module, use_arrays=False)

    @guppy(module)
    def foo(q1: qubit, q2: qubit) -> bool:
        return  guppy_circ(q1, q2)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_register_arrays_default(validate):
    from pytket import Circuit

    circ = Circuit(2)

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module)

    @guppy(module)
    def foo(default_reg: array[qubit, 2]) -> None:
        return guppy_circ(default_reg)

    # print(module.compile_hugr().render_dot())
    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_register_arrays(validate):
    from pytket import Circuit

    circ = Circuit(2)
    reg = circ.add_q_register("extra_reg", 3)
    circ.measure_register(reg, "extra_bits")

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module)

    @guppy(module)
    def foo(default_reg: array[qubit, 2], 
            extra_reg: array[qubit, 3]) -> array[bool, 3]:
        # Note that the default_reg name is 'q' so it has to come after 'e...' 
        # lexicographically.
        return guppy_circ(extra_reg, default_reg)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_register_arrays_multiple_measure(validate):
    from pytket import Circuit

    circ = Circuit(2)
    reg1 = circ.add_q_register("extra_reg1", 3)
    reg2 = circ.add_q_register("extra_reg2", 2)
    circ.measure_register(reg1, "extra_bits1")
    circ.measure_register(reg2, "extra_bits2")

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module)

    @guppy(module)
    def foo(default_reg: array[qubit, 2], 
            extra_reg1: array[qubit, 3]) -> tuple[array[bool, 3], array[bool, 2]]:
        extra_reg2 = array(qubit(), qubit())
        result = guppy_circ(extra_reg1, extra_reg2, default_reg)
        # Until we add linearity checks to loaded circuits need to discard owned 
        # arrays.
        discard_array(extra_reg2) 
        return result

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_register_arrays_mixed(validate):
    from pytket import Circuit

    circ = Circuit(2, 1)
    reg = circ.add_q_register("q2", 3)
    circ.measure_register(reg, "c2")
    circ.Measure(0, 0)

    module = GuppyModule("test")
    module.load_all(quantum)

    guppy.load_pytket("guppy_circ", circ, module)

    @guppy(module)
    def foo(q: array[qubit, 2], 
            q2: array[qubit, 3]) -> tuple[array[bool, 1], array[bool, 3]]:
        return guppy_circ(q, q2)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_compile_sig(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy.pytket(circ, module)
    def guppy_circ(q1: qubit) -> None: ...

    validate(guppy_circ.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_compile_load(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    pytket_func = guppy.load_pytket("guppy_circ", circ, module, use_arrays=False)

    validate(pytket_func.compile())
