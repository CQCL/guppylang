from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    a, = 1
    return a
