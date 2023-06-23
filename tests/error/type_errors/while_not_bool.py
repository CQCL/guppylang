from tests.error.util import guppy


@guppy
def foo() -> int:
    while 42:
        pass
    return 0
