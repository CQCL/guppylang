from tests.error.util import guppy


@guppy
def foo(xs: list[int]) -> int:
    for _ in xs:
        y = 5
    return y
