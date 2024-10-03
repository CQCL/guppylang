import pytest
from guppylang import qubit, guppy, GuppyModule
from guppylang.prelude.builtins import owned

from tests.util import compile_guppy


def test_types(validate):
    @compile_guppy
    def test(
        xs: list[int], ys: list[tuple[int, float]]
    ) -> tuple[list[int], list[tuple[int, float]]]:
        return xs, ys

    validate(test)


def test_len(validate):
    @compile_guppy
    def test(xs: list[int]) -> int:
        return len(xs)

    validate(test)


def test_literal(validate):
    @compile_guppy
    def test(x: float) -> list[float]:
        return [1.0, 2.0, 3.0, 4.0 + x]

    validate(test)


def test_push_pop(validate):
    @compile_guppy
    def test(xs: list[int]) -> bool:
        xs.append(3)
        x = xs.pop()
        return x == 3

    validate(test)


@pytest.mark.skip("See https://github.com/CQCL/guppylang/issues/528")
def test_arith(validate):
    @compile_guppy
    def test(xs: list[int]) -> list[int]:
        xs += xs + [42]
        xs = 3 * xs
        return xs * 4

    validate(test)


def test_subscript(validate):
    @compile_guppy
    def test(xs: list[float], i: int) -> float:
        return xs[2 * i]

    validate(test)


def test_linear(validate):
    module = GuppyModule("test")
    module.load(qubit)

    @guppy(module)
    def test(xs: list[qubit], q: qubit @owned) -> int:
        xs.append(q)
        return len(xs)

    validate(module.compile())
