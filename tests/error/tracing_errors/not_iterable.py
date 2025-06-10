from guppylang.decorator import guppy


@guppy.comptime
def test(x: int) -> None:
    for _ in x:
        pass


guppy.compile(test)
