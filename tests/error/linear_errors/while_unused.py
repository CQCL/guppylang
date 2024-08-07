import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def test(n: int) -> None:
    q = qubit()
    i = 0
    while i < n:
        q = h(q)
        i += 1


module.compile()
