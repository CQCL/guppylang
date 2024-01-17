from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    while x:
        if x:
            pass
        else:
            return -1
    return 0
