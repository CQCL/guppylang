from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit, state_result)

@guppy(module)
@no_type_check
def main(qs: array[qubit, 3], rs: array[qubit, 4]) -> None:
   state_result("foo", qs, rs)

module.compile()