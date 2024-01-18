from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    y = 3
    if x:
        y += 1
    else:
        y = True
    return y
