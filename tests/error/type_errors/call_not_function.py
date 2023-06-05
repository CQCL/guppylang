from tests.error.util import guppy


@guppy
def foo(x: int) -> int:
    x(42)
    return 0
