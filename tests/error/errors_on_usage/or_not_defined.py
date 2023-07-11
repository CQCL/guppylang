from tests.error.util import guppy


@guppy
def foo(x: bool, y: int) -> int:
    if x or (z := y + 1):
        return z
    else:
        return z
