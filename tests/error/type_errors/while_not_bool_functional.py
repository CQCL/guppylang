from guppy.decorator import guppy


@guppy
def foo() -> int:
    _@functional
    while 42:
        pass
    return 0
