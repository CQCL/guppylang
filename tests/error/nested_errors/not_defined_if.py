from tests.util import compile_guppy


@compile_guppy
def foo(b: bool) -> int:
    if b:
        def bar() -> int:
            return 0
    return bar()
