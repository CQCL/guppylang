import pytest

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum_functional as quantum
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def test() -> array[int, 10]:
        return array(i + 1 for i in range(10))

    validate(test)


def test_basic_linear(validate):
    module = GuppyModule("test")
    module.load_all(quantum)
    module.load(qubit)

    @guppy(module)
    def test() -> array[qubit, 42]:
        return array(qubit() for _ in range(42))

    validate(module.compile())


def test_zero_length(validate):
    @compile_guppy
    def test() -> array[float, 0]:
        return array(i / 0 for i in range(0))

    validate(test)


def test_capture(validate):
    @compile_guppy
    def test(x: int) -> array[int, 42]:
        return array(i + x for i in range(42))

    validate(test)


@pytest.mark.skip("See https://github.com/CQCL/hugr/issues/1625")
def test_capture_struct(validate):
    module = GuppyModule("test")

    @guppy.struct(module)
    class MyStruct:
        x: int
        y: float

    @guppy(module)
    def test(s: MyStruct) -> array[int, 42]:
        return array(i + s.x for i in range(42))

    validate(module.compile())


def test_scope(validate):
    @compile_guppy
    def test() -> float:
        x = 42.0
        array(x for x in range(10))
        return x

    validate(test)


def test_nested_left(validate):
    @compile_guppy
    def test() -> array[array[int, 10], 20]:
        return array(array(x + y for y in range(10)) for x in range(20))

    validate(test)
