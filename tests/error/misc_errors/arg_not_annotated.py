from tests.util import compile_guppy


@compile_guppy
def foo(x: bool, y) -> int:
    return y
