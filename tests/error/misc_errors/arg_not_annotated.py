from tests.error.util import guppy


@guppy
def foo(x: bool, y) -> int:
    return y
