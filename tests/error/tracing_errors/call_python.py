from guppylang.decorator import guppy


@guppy.comptime
def foo() -> None:
    pass


guppy.compile(foo)

foo()
