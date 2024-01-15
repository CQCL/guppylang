from guppy.decorator import guppy


@guppy
def foo() -> int:
    return py()
