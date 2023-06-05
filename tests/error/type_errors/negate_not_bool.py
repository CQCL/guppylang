from tests.error.util import guppy


@guppy
def foo() -> bool:
    return not "xxx"
