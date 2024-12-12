"""Tests for using python expressions in guppy functions."""

from importlib.util import find_spec

import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import py, array, nat
from guppylang.std import quantum
from guppylang.std.quantum import qubit
from tests.util import compile_guppy

tket2_installed = find_spec("tket2") is not None


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


def test_list_basic(validate):
    @compile_guppy
    def foo() -> array[int, 3]:
        xs = py([1, 2, 3])
        return xs

    validate(foo)


def test_list_empty(validate):
    @compile_guppy
    def foo() -> array[int, 0]:
        return py([])

    validate(foo)


def test_list_empty_nested(validate):
    @compile_guppy
    def foo() -> None:
        xs: array[tuple[int, array[bool, 0]], 1] = py([(42, [])])

    validate(foo)


def test_list_empty_multiple(validate):
    @compile_guppy
    def foo() -> None:
        xs: tuple[array[int, 0], array[bool, 0]] = py([], [])

    validate(foo)


def test_nats_from_ints(validate):
    @compile_guppy
    def foo() -> None:
        x: nat = py(1)
        y: tuple[nat, nat] = py(2, 3)
        z: list[nat] = py([4, 5, 6])

    validate(foo)


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
@pytest.mark.skip("Fails because of extensions in types #343")
def test_pytket_single_qubit(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def foo(q: qubit) -> qubit:
        f = py(circ)
        return f(q)

    validate(module.compile())


@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
@pytest.mark.skip("Fails because of extensions in types #343")
def test_pytket_multi_qubit(validate):
    from pytket import Circuit

    circ = Circuit(3)
    circ.CX(0, 1)
    circ.H(2)
    circ.T(0)
    circ.CZ(2, 0)

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def foo(q1: qubit, q2: qubit, q3: qubit) -> tuple[qubit, qubit, qubit]:
        return py(circ)(q1, q2, q3)

    validate(module.compile())


@pytest.mark.skip(
    "Now requires a conversion pass to turn TKET1 measurements into TKET2 measurements"
)
@pytest.mark.skipif(not tket2_installed, reason="Tket2 is not installed")
def test_pytket_measure(validate):
    from pytket import Circuit

    circ = Circuit(1)
    circ.H(0)
    circ.measure_all()

    module = GuppyModule("test")
    module.load_all(quantum)

    @guppy(module)
    def foo(q: qubit) -> tuple[qubit, bool]:
        return py(circ)(q)

    validate(module.compile())


def test_func_type_arg(validate):
    module = GuppyModule("test")
    n = 10

    @guppy(module)
    def foo(xs: array[int, py(n)]) -> array[int, py(n)]:
        return xs

    @guppy.declare(module)
    def bar(xs: array[int, py(n)]) -> array[int, py(n)]: ...

    @guppy.struct(module)
    class Baz:
        xs: array[int, py(n)]

    validate(module.compile())
