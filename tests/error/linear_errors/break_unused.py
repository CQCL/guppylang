import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def new_qubit() -> Qubit:
    ...


@guppy.declare(module)
def measure_() -> bool:
    ...


@guppy(module)
def foo(i: int) -> bool:
    b = False
    while True:
        q = new_qubit()
        if i == 0:
            break
        i -= 1
        b ^= measure_(q)
    return b


module.compile()
