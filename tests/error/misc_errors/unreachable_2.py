from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> int:
    if x:
        return 4
    else:
        return 1
    x = 42
