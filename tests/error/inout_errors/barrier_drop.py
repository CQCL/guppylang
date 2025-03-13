from typing import no_type_check
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import barrier
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load(qubit)

@guppy(module)
@no_type_check
def main() -> None:
   barrier(qubit())


module.compile()
