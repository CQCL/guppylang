from guppy.decorator import guppy


@guppy
def foo() -> int:
    return py(1 / 0)
