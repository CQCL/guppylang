from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    while x:
        y = 5
    return y
