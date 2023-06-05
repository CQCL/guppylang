from tests.error.util import guppy


@guppy
def foo() -> int:
    if 42:
        return 0
    return 1
