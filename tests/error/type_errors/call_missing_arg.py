from guppylang.decorator import guppy


@guppy
def foo(x: int) -> int:
    return foo()


guppy.compile(foo)
