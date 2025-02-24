from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")


@guppy.comptime(module)
def test(xs: array[int, 10]) -> None:
    xs.pop()


module.compile()
