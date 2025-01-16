from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")

@guppy(module)
def foo(xs: array[array[int, 10], 20]) -> array[int, 10]:
    return xs[0]

module.compile()
