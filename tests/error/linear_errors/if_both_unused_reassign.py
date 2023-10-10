import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def new_qubit() -> Qubit:
    ...


@guppy(module)
def foo(b: bool) -> Qubit:
    if b:
        q = new_qubit()
    else:
        q = new_qubit()
    q = new_qubit()
    return q


module.compile(True)
