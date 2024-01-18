from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    if x:
        y = 1
    return y
