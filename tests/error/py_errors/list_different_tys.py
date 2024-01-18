from guppylang.decorator import guppy


@guppy
def foo() -> int:
    return py([1, 1.0])
