from guppylang.decorator import guppy


@compile_guppy
def foo(x: bool) -> int:
    y = 5
    _@functional
    while x:
        y = True
    return y
