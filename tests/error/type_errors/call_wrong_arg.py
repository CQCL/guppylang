from guppy.decorator import guppy


@guppy
def foo(x: int) -> int:
    return foo(True)
