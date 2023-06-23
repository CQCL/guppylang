from tests.error.util import guppy


@guppy
def foo() -> int:
    a, b, c = 1, True
    return a
