from guppylang.decorator import guppy


@guppy
def foo(x: int) -> int:
    return foo(True)


guppy.compile(foo)
