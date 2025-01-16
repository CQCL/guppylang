from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned


module = GuppyModule("test")

@guppy(module)
def main(xs: array[int, 2] @ owned) -> array[int, 2]:
   ys = xs
   return xs

module.compile()
