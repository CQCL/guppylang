from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> int:
    a, *bs = xs
    return a
