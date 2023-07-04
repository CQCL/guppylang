from guppy.compiler import guppy, GuppyModule
from tests.integration.util import validate, functional, _


def test_factorial():
    @guppy
    def factorial1(x: int) -> int:
        acc = 1
        while x > 0:
            acc *= x
            x -= 1
        return acc

    @guppy
    def factorial2(x: int) -> int:
        if x == 0:
            return 1
        return factorial2(x - 1) * x

    @guppy
    def factorial3(x: int, acc: int) -> int:
        if x == 0:
            return acc
        return factorial3(x - 1, acc * x)

    # @guppy
    # def factorial4(x: int) -> int:
    #     acc = 1
    #     _@functional
    #     while x > 0:
    #         acc *= x
    #         x -= 1
    #     return acc

    validate(factorial1)
    validate(factorial2)
    validate(factorial3)
    # validate(factorial4)


def test_even_odd():
    module = GuppyModule("module")

    @module
    def is_even(x: int) -> bool:
        if x == 0:
            return True
        return is_odd(x - 1)

    @module
    def is_odd(x: int) -> bool:
        if x == 0:
            return False
        return is_even(x - 1)

    validate(module.compile(exit_on_error=True))
