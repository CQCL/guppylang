import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def new_qubit() -> Qubit:
    ...


@guppy(module)
def measure(q: Qubit) -> bool:
    ...


@guppy(module)
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


module.compile(True)
