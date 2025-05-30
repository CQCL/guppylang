from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy
def foo(x: T) -> None:
    y = T


guppy.compile(foo)
