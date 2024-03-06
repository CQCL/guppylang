from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo() -> list[qubit]:
    return []


module.compile()
