from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    if x:
        y = 1
    return y
