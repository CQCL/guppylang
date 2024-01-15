from guppy.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    _@functional
    if 42:
        return 0
    return 1
