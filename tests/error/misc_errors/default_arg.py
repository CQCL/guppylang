from tests.util import compile_guppy


@compile_guppy
def foo(x: int, y: bool = True) -> int:
    return x
