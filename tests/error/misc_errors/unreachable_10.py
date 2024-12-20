from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    while True:
        x += 1
    return x
