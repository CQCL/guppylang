from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    if False and (x := x + 1):
        pass
    return x
