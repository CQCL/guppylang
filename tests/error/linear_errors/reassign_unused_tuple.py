import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def new_qubit() -> Qubit:
    ...


@guppy(module)
def foo(q: Qubit) -> tuple[Qubit, Qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile()
