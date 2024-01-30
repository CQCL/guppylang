from guppylang.decorator import guppy


@compile_guppy
def foo(x: bool) -> int:
    _@functional
    if x:
        y = 1
    else:
        z = 2
    return z
