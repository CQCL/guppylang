from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def test(x: int) -> None:
    for _ in x:
        pass


module.compile()
