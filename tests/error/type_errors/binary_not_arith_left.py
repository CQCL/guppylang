from guppylang.decorator import guppy


@guppy
def foo(x: int) -> int:
    return (1, 1) * 4
