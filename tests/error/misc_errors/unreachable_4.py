from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    while x:
        continue
        x = 42
