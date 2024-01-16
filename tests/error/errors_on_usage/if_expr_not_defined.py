from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    (y := 1) if x else 0
    return y
