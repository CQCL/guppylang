from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    y = 3
    if x:
        y = False
    z = y
    return 42
