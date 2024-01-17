from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    y = 5
    while x:
        y = True
    return y
