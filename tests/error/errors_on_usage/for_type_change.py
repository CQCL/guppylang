from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> int:
    y = 5
    for x in xs:
        y = True
    return y
