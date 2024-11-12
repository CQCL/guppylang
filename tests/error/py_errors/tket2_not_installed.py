from pytket import Circuit

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

circ = Circuit(1)
circ.H(0)

module = GuppyModule("test")
module.load(qubit)


@guppy(module)
def foo(q: qubit) -> qubit:
    f = py(circ)
    return f(q)


module.compile()
