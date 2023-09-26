import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module.declare
def new_qubit() -> Qubit:
    ...


@module.declare
def measure(q: Qubit) -> bool:
    ...


@module
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


module.compile(True)
