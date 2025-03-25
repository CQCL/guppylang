from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class S:
    x: int


@guppy.comptime(module)
def test() -> S:
    s = S(1)
    s.x = 1.0
    return s


module.compile()
