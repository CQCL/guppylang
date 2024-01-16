from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    while x:
        break
        x = 42
