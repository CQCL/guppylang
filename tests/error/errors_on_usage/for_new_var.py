from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> int:
    for _ in xs:
        y = 5
    return y
