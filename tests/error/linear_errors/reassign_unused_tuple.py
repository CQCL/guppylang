import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def new_qubit() -> Qubit:
    ...


@guppy(module)
def foo(q: Qubit) -> tuple[Qubit, Qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile(True)
