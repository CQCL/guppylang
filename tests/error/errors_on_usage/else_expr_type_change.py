from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    y = 3
    (y := y + 1) if x else (y := True)
    return y
