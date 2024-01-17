from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    while x:
        break
        x = 42
