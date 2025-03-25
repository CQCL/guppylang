from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: T) -> T: ...


@guppy.comptime(module)
def test() -> int:
    return foo[int](0)


module.compile()
