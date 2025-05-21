from guppylang import array
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")
n = guppy.nat_var("n", module)


@guppy.comptime(module)
def test(xs: array[int, n]) -> None:
    pass


module.compile()
