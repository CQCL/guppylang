from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    (y := 1) if x else 0
    return y
