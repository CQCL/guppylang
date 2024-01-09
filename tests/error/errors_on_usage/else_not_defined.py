from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    if x:
        y = 1
    else:
        z = 2
    return z
