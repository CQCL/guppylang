from guppy.decorator import guppy


@guppy
def foo() -> int:
    _@functional
    if 42:
        return 0
    return 1
