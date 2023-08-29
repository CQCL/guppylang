from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    (y := 1) if x else (z := 2)
    return z
