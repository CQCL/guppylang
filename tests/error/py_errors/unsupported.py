from guppylang.decorator import guppy


@guppy
def foo() -> int:
    return py({1, 2, 3})
