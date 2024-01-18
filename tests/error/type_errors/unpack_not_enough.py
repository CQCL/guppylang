from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    a, b, c = 1, True
    return a
