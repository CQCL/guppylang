from pytket import Circuit

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

circ = Circuit(2)
circ.X(0)
circ.Y(1)

module = GuppyModule("test")
module.load(qubit)

@guppy.pytket(circ, module)
def guppy_circ(q: qubit) -> None: ...

@guppy(module)
def foo(q: qubit) -> None:
    guppy_circ(q)


module.compile()