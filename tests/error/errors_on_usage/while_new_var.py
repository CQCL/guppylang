from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    while x:
        y = 5
    return y
