import guppy.prelude.quantum as quantum

from guppy.compiler import GuppyModule, guppy
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def new_qubit() -> Qubit:
    ...


@guppy(module)
def measure() -> bool:
    ...


@guppy(module)
def foo(i: int) -> bool:
    b = False
    while i > 0:
        q = new_qubit()
        if i % 10 == 0:
            break
        i -= 1
        b ^= measure(q)
    return b


module.compile(True)
