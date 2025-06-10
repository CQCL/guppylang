from guppylang.decorator import guppy


@guppy.declare
def foo(x: int, y: int) -> None: ...


@guppy.comptime
def test() -> None:
    foo(1, 2, 3, 4)


guppy.compile(test)
