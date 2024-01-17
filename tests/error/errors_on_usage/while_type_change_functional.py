from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    y = 5
    _@functional
    while x:
        y = True
    return y
