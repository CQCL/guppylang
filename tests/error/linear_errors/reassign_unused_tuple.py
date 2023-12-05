import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit


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
