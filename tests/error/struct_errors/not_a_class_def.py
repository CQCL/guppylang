from guppylang.decorator import guppy


@guppy.struct
def foo(x: int) -> int:
    return x


guppy.compile(foo)
