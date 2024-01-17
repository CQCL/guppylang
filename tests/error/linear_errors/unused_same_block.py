import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: Qubit) -> int:
    x = q
    x = 10
    return x


module.compile()
