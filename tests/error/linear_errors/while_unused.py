from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import quantum, qubit
from guppylang.prelude.quantum_functional import h

module = GuppyModule("test")
module.load_all(quantum)
module.load(h)


@guppy(module)
def test(n: int) -> None:
    q = qubit()
    i = 0
    while i < n:
        q = h(q)
        i += 1


module.compile()
