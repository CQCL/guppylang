import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def new_qubit() -> Qubit:
    ...


@guppy.declare(module)
def measure() -> bool:
    ...


@guppy(module)
def foo(i: int) -> bool:
    b = False
    while True:
        q = new_qubit()
        if i == 0:
            break
        i -= 1
        b ^= measure(q)
    return b


module.compile()
