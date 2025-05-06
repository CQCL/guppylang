from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.debug import state_result

module = GuppyModule("test")
module.load(state_result)

@guppy(module)
@no_type_check
def main(xs: array[int, 3]) -> None:
   state_result("foo", xs)

module.compile()