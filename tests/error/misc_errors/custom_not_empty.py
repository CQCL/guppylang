from guppylang.decorator import guppy


@guppy.custom()
def foo(x: int) -> int:
    return x


guppy.compile(foo)
