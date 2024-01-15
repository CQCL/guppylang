from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    _@functional
    while x:
        if x:
            pass
        else:
            return -1
    return 0
