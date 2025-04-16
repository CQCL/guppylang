from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned
from guppylang.std.debug import state_result
from guppylang.std.quantum import qubit, discard_array

module = GuppyModule("test")
module.load(qubit, discard_array, state_result)

@guppy(module)
@no_type_check
def main(qs: array[qubit, 3] @ owned) -> None:
   ys = qs
   state_result("foo", qs)
   discard_array(qs)
   discard_array(ys)

module.compile()
