from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    if x:
        y = 1
    else:
        y = False
    return y
