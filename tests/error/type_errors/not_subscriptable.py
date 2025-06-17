from guppylang.decorator import guppy


@guppy
def foo(x: int) -> None:
    x[0]


guppy.compile(foo)
