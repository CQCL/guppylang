from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test() -> int:
    if True:
        return 1.0
    else:
        return 1


module.compile()
