from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.quantum_functional import h

module = GuppyModule("test")
module.load(qubit, h)


@guppy(module)
def test(n: int) -> None:
    q = qubit()
    i = 0
    while i < n:
        q = h(q)
        i += 1


module.compile()
