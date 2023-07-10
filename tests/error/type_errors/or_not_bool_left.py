from tests.error.util import guppy


@guppy
def foo(x: bool) -> bool:
    return "xx" or x
