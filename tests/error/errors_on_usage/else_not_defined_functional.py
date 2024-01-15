from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    if x:
        y = 1
    else:
        z = 2
    return z
