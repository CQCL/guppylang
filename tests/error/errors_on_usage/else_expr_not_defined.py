from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    (y := 1) if x else (z := 2)
    return z
