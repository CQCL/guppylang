from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure, cx, h

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def test(q: qubit @ owned, x: int) -> int: # type: ignore
    r = qubit()
    cx(q, r)
    a = measure(q)
    h(q)
    b = measure(r)
    return int(a) + int(b) + x

module.compile()
