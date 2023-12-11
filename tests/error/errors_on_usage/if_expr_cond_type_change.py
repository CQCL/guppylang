from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    y = 4
    0 if (y := x) else (y := 6)
    z = y
    return 42
