from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    a, b = 1, True, 3.0
    return a
