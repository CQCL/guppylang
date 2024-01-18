from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    y = 3
    if x:
        y = False
    z = y
    return 42
