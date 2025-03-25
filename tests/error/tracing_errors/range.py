from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(n: int) -> int:
    s = 0
    for i in range(n):
        s += 1
    return s


module.compile()
