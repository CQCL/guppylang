from tests.util import compile_guppy


@compile_guppy
def foo(x: bool, y: int) -> int:
    if x and (z := y + 1):
        return z
    else:
        return z
