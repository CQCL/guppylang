from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    return (1, 1) * 4
