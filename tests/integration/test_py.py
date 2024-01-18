import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import Qubit, quantum
from tests.integration.util import py
from tests.util import compile_guppy


try:
    import tket2

    tket2_installed = True
except ImportError:
    tket2_installed = False


def test_basic(validate):
    x = 42

    @compile_guppy
    def foo() -> int:
        return py(x + 1)

    validate(foo)


def test_builtin(validate):
    @compile_guppy
    def foo() -> int:
        return py(len({"a": 1337, "b": None}))

    validate(foo)


def test_if(validate):
    b = True

    @compile_guppy
    def foo() -> int:
        if py(b or 1 > 6):
            return 0
        return 1

    validate(foo)


def test_redeclare_after(validate):
    x = 1

    @compile_guppy
    def foo() -> int:
        return py(x)

    x = False

    validate(foo)


def test_tuple(validate):
    @compile_guppy
    def foo() -> int:
        x, y = py((1, False))
        return x

    validate(foo)


def test_tuple_implicit(validate):
    @compile_guppy
    def foo() -> int:
        x, y = py(1, False)
        return x

    validate(foo)


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_pytket_single_qubit(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def foo(q: Qubit) -> Qubit:
        f = py(circ)
        return f(q)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_pytket_multi_qubit(validate):
    from pytket import Circuit

    circ = Circuit(3)
    circ.CX(0, 1)
    circ.H(2)
    circ.T(0)
    circ.CZ(2, 0)

    module = GuppyModule("test")
    module.load(quantum)

    @guppy(module)
    def foo(q1: Qubit, q2:Qubit, q3:Qubit) -> tuple[Qubit, Qubit, Qubit]:
        return py(circ)(q1, q2, q3)

    validate(module.compile())
