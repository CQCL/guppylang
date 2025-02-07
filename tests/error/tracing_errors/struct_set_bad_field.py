from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class S:
    x: int


@guppy.comptime(module)
def test(x: int) -> None:
    s = S(x)
    s.y = x


module.compile()
