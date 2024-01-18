from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    def bar() -> int:
        return x

    return bar()
