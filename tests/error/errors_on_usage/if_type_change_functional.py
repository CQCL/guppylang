from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    y = 3
    _@functional
    if x:
        y = False
    return y
