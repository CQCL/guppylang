import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module.declare
def new_qubit() -> Qubit:
    pass


@module
def foo(b: bool) -> Qubit:
    if b:
        q = new_qubit()
    else:
        q = new_qubit()
    q = new_qubit()
    return q


module.compile(True)
