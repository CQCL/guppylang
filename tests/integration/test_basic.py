from guppy.compiler import guppy
from tests.integration.util import validate


def test_id():
    @guppy
    def identity(x: int) -> int:
        return x

    validate(identity)


def test_void():
    @guppy
    def void() -> None:
        return

    validate(void)


def test_copy():
    @guppy
    def copy(x: int) -> (int, int):
        return x, x

    validate(copy)


def test_discard():
    @guppy
    def discard(x: int) -> None:
        return

    validate(discard)


def test_implicit_return():
    @guppy
    def ret() -> None:
        pass

    validate(ret)


def test_assign():
    @guppy
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo)
