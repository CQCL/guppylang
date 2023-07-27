from tests.error.util import guppy


@guppy
def foo(x: int) -> int:
    y = x + 1

    def bar() -> None:

        def baz() -> None:
            y += 2

        baz()

    bar()
    return y

