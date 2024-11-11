from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
def foo(x: int) -> int:
    return x


module.compile()
