from guppy.decorator import guppy


@guppy
def foo(x: int) -> int:
    return x(42)
