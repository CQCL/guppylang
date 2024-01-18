from tests.util import compile_guppy


@compile_guppy
def foo(x: bool) -> None:
    y = True if x else 42
