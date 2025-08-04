from pytket import Circuit

from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

circ = Circuit(2)
circ.X(0)
circ.Y(1)


guppy_circ = guppy.load_pytket("guppy_circ", circ, use_arrays=False)

@guppy
def foo(q: qubit, p: qubit) -> None:
    guppy_circ(q, p)


foo.compile()