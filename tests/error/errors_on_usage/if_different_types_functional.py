from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    if x:
        y = 1
    else:
        y = False
    return y
