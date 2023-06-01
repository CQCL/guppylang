from guppy.compiler import guppy
from tests.integration.util import validate


def test_id(tmp_path):
    @guppy
    def identity(x: int) -> int:
        return x

    validate(identity, tmp_path)


def test_void(tmp_path):
    @guppy
    def void() -> None:
        return

    validate(void, tmp_path)


def test_copy(tmp_path):
    @guppy
    def copy(x: int) -> (int, int):
        return x, x

    validate(copy, tmp_path)


def test_discard(tmp_path):
    @guppy
    def discard(x: int) -> None:
        return

    validate(discard, tmp_path)


def test_implicit_return(tmp_path):
    @guppy
    def ret() -> None:
        pass

    validate(ret, tmp_path)


def test_assign(tmp_path):
    @guppy
    def foo(x: bool) -> bool:
        y = x
        return y

    validate(foo, tmp_path)



