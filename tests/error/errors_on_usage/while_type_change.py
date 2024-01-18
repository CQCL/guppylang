from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    y = 5
    while x:
        y = True
    return y
