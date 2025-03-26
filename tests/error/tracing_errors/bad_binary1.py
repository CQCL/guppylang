from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(x: int) -> int:
    return x + (2, 3)


module.compile()
