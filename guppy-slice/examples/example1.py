from guppylang import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.builtins import owned, array
from guppylang.std.quantum import qubit, measure, cx, cz, h, discard

test_module = GuppyModule("test")
test_module.load_all(quantum)

@guppy(test_module)
def test(q1: qubit @ owned, q2: qubit, q3: qubit, x: int) -> int:  # type: ignore
    xs = array(x, 0, 0)
    r = qubit()
    cx(q1, r)
    h(q2)
    cz(q1, q2)
    cx(q2, q3)
    if xs[0] == 0:
        a = measure(q1)
        discard(r)
    else:
        a = measure(r)
        discard(q1)
    return int(a)
