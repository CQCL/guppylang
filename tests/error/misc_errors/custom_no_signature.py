from guppylang.decorator import guppy


@guppy.custom()
def foo(x): ...


foo.compile()
