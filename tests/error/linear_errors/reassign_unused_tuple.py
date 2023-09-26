import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module.declare
def new_qubit() -> Qubit:
    pass


@module
def foo(q: Qubit) -> tuple[Qubit, Qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile(True)
