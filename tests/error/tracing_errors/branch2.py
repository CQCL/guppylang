from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.declare(module)
def foo() -> int: ...


@guppy.comptime(module)
def test() -> int:
    if foo() > 1:
        return 1
    return 0


module.compile()
