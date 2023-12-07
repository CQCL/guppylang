from tests.error.util import guppy


@guppy
def foo(b: bool) -> int:
    if b:
        def bar() -> int:
            return 0
    return bar()
