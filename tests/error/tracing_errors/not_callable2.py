from guppylang.decorator import guppy

x = guppy.extern("x", "float")


@guppy.comptime
def test() -> None:
    x(1)


guppy.compile(test)
