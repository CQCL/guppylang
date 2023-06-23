from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    y = 5
    _@functional
    while x:
        y = True
    return y
