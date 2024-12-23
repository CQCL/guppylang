from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    while not False:
        if True:
            break
        x += 1
    return x
