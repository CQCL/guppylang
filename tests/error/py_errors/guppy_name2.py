from guppylang.decorator import guppy


x = 42


@guppy
def foo(x: int) -> int:
    return py(x + 1)
