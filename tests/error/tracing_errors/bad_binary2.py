from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(x: int) -> int:
    return (1, 2) + x


module.compile()
