from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.declare(module)
def foo(x: int, y: int) -> None: ...


@guppy.comptime(module)
def test() -> None:
    foo(1)


module.compile()
