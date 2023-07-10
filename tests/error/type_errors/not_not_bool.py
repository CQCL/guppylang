from tests.error.util import guppy


@guppy
def foo(x: bool) -> bool:
    return not "x"
