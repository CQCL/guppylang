from tests.error.util import guppy


@guppy
def foo() -> int:
    def bar() -> int:
        return x

    return bar()
