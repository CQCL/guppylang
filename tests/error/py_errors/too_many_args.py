from tests.error.util import guppy


@guppy
def foo() -> int:
    return py(1, 2)
