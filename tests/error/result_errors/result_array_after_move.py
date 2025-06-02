from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, result

module = GuppyModule("test")


@guppy(module)
@no_type_check
def main() -> None:
   xs = array(1, 2, 3)
   ys = xs
   result("foo", xs)


module.compile()
