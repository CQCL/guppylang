import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module.declare
def new_qubit() -> Qubit:
    pass


@module.declare
def measure() -> bool:
    pass


@module
def foo(i: int) -> bool:
    b = False
    while True:
        q = new_qubit()
        if i == 0:
            break
        i -= 1
        b ^= measure(q)
    return b


module.compile(True)
