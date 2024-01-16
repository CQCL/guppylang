from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    y = 3
    if x:
        y = False
    z = y
    return 42
