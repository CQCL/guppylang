from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    if not False:
        x += 1
    else:
        x -= 1
    return x
