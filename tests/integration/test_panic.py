from guppylang import GuppyModule, guppy
from guppylang.std.builtins import panic
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main() -> None:
        panic("I panicked!")

    validate(main)


def test_discard(validate):
    @compile_guppy
    def main() -> None:
        a = 1 + 2
        panic("I panicked!", False, a)

    validate(main)


def test_value(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo() -> int:
        return panic("I panicked!")

    @guppy(module)
    def bar() -> tuple[int, float]:
        return panic("I panicked!")

    @guppy(module)
    def baz() -> None:
        return panic("I panicked!")

    validate(module.compile())
