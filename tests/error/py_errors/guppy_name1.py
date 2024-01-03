from guppy.decorator import guppy


@guppy
def foo(x: int) -> int:
    return py(x + 1)
