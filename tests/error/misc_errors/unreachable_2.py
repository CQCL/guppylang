from tests.error.util import guppy


@guppy
def foo(x: bool) -> int:
    if x:
        return 4
    else:
        return 1
    x = 42
