from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")

n = guppy.nat_var("n", module=module)


@guppy.declare(module)
def foo(x: array[int, n]) -> None:
    ...


@guppy(module)
def main(xs: array[int, 42]) -> None:
    foo[43](xs)


module.compile()
