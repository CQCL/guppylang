from guppy.decorator import guppy


@guppy
def foo(x: bool) -> None:
    y = True if x else 42
