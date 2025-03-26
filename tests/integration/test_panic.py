from guppylang import GuppyModule, guppy
from guppylang.std.builtins import panic, exit
from tests.util import compile_guppy


def test_basic(validate):
    @compile_guppy
    def main() -> None:
        panic("I panicked!")
        exit( "I panicked!", 1)

    validate(main)


def test_discard(validate):
    @compile_guppy
    def main() -> None:
        a = 1 + 2
        panic("I panicked!", False, a)
        exit("I exited!", 2, False, a)

    validate(main)


def test_value(validate):
    module = GuppyModule("test")

    @guppy(module)
    def foo() -> int:
        return exit("I exited!", 1)

    @guppy(module)
    def bar() -> tuple[int, float]:
        return panic("I panicked!")

    @guppy(module)
    def baz() -> None:
        return panic("I panicked!")

    validate(module.compile())


def test_py_message(validate):
    @compile_guppy
    def main(x: int) -> None:
        panic(py("I" + "panicked" + "!"))
        exit(py("I" + "exited" + "!"), 0)

    validate(main)
