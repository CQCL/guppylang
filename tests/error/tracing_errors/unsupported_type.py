from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.declare(module)
def foo(x: int) -> int: ...


@guppy.comptime(module)
def test() -> None:
    foo(set())


module.compile()
