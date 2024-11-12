from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")

n = guppy.nat_var("n", module=module)


@guppy.declare(module)
def foo(x: array[int, n], y: array[int, n]) -> None:
    ...


@guppy(module)
def main(x: array[int, 42], y: array[int, 43]) -> None:
    foo(x, y)


module.compile()
