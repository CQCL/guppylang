from tests.error.util import guppy


@guppy
def foo(x: bool) -> None:
    y = True if x else 42
