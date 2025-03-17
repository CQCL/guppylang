from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")

S = guppy.type_var("S", module=module)
T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: S, y: T) -> None:
    ...


@guppy(module)
def main(x: int, y: float) -> None:
    foo[float, int](x, y)


module.compile()
