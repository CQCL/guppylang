from tests.error.util import guppy


@guppy
def foo(x: float) -> int:
    return 1 if x else 0
