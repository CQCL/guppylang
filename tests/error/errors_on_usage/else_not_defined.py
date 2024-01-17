from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    if x:
        y = 1
    else:
        z = 2
    return z
