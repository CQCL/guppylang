from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.declare(module)
def foo() -> None: ...


@guppy.comptime(module)
def test() -> None:
    foo[0]()


module.compile()
