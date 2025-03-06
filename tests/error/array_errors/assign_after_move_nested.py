from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")


@guppy(module)
def main() -> None:
   xs = array(array(1, 2, 3), array(1, 2, 3))
   ys = xs
   xs[0][0] = 0


module.compile()
