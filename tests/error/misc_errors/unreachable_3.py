from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    while x:
        break
        x = 42
