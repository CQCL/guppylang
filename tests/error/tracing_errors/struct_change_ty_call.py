from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class S:
    x: int


@guppy.declare(module)
def foo(s: S) -> None: ...


@guppy.comptime(module)
def test() -> None:
    s = S(1)
    s.x = 1.0
    foo(s)


module.compile()
