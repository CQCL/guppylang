from guppylang.decorator import guppy


@guppy.custom()
def foo(x): ...


guppy.compile(foo)
