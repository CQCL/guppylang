from guppylang.decorator import guppy


@guppy.comptime
def test() -> int:
    return 1.0


guppy.compile(test)
