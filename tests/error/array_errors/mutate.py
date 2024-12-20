from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned


module = GuppyModule("test")


@guppy(module)
def main(xs: array[int, 10]) -> None:
    xs[0] = 1


module.compile()
