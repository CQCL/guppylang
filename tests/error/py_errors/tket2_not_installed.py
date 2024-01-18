from pytket import Circuit

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import quantum, Qubit

circ = Circuit(1)
circ.H(0)

module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: Qubit) -> Qubit:
    f = py(circ)
    return f(q)


module.compile()
