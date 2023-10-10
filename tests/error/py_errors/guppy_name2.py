from tests.error.util import guppy


x = 42


@guppy
def foo(x: int) -> int:
    return py(x + 1)
