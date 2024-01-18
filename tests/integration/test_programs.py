from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from tests.util import compile_guppy


def test_factorial(validate):
    @compile_guppy
    def factorial1(x: int) -> int:
        acc = 1
        while x > 0:
            acc *= x
            x -= 1
        return acc

    @compile_guppy
    def factorial2(x: int) -> int:
        if x == 0:
            return 1
        return factorial2(x - 1) * x

    @compile_guppy
    def factorial3(x: int, acc: int) -> int:
        if x == 0:
            return acc
        return factorial3(x - 1, acc * x)

    validate(factorial1, name="factorial1")
    validate(factorial2, name="factorial2")
    validate(factorial3, name="factorial3")


def test_even_odd(validate):
    module = GuppyModule("module")

    @guppy(module)
    def is_even(x: int) -> bool:
        if x == 0:
            return True
        return is_odd(x - 1)

    @guppy(module)
    def is_odd(x: int) -> bool:
        if x == 0:
            return False
        return is_even(x - 1)

    validate(module.compile())
