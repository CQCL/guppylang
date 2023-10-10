import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: Qubit) -> tuple[Qubit, Qubit]:
    return q, q


module.compile(True)
