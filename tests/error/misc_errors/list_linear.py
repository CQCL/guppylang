from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.prelude.quantum import Qubit

import guppy.prelude.quantum as quantum


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo() -> list[Qubit]:
    return []


module.compile()
