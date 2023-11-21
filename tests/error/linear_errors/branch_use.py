import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def new_qubit() -> Qubit:
    ...


@guppy.declare(module)
def measure(q: Qubit) -> bool:
    ...


@guppy(module)
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


module.compile()
