from guppy.decorator import guppy


@guppy
def foo(x: bool, y) -> int:
    return y
