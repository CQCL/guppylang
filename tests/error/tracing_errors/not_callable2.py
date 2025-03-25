from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")

x = guppy.extern("x", "float", module=module)


@guppy.comptime(module)
def test() -> None:
    x(1)


module.compile()
