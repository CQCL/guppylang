import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module.declare
def new_qubit() -> Qubit:
    pass


@module
def foo(q: Qubit) -> Qubit:
    q = new_qubit()
    return q


module.compile(True)
