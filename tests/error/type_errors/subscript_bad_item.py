from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array

module = GuppyModule("test")


@guppy(module)
def foo(xs: array[int, 42]) -> int:
    return xs[1.0]


module.compile()
