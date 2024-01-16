from guppylang.decorator import guppy


@guppy
def foo() -> int:
    a, b, c = 1, True
    return a
