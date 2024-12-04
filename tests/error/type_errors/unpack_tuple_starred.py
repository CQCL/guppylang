from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    a, *bs = 1, 2, True
    return a
