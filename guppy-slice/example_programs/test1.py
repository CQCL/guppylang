from guppylang import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure, cx, h

test_module = GuppyModule("test")
test_module.load_all(quantum)

@guppy(test_module)
def test(q: qubit @ owned, x: int) -> int: # type: ignore
    r = qubit()
    cx(q, r)
    a = measure(q)
    # h(q)
    b = measure(r)
    return int(a) + int(b) + x
