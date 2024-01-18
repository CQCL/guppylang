from tests.util import compile_guppy


@compile_guppy
def foo(x: int) -> int:
    y = x + 1

    def bar() -> None:
        if 3 > 2:
            z = y
        y = 2

    bar()
    return y
