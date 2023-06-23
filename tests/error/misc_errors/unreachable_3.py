from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    while x:
        break
        x = 42
