from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(x: bool) -> int:
    return 1 if x else 0


module.compile()
