import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: Qubit) -> int:
    x = q
    x = 10
    return x


module.compile(True)
