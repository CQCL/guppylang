from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test() -> int:
    return 1.0


module.compile()
