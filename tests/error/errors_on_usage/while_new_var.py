from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    while x:
        y = 5
    return y
