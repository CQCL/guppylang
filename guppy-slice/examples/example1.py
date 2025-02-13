from guppylang import guppy
from guppylang.module import GuppyModule
from guppylang.std import quantum
from guppylang.std.builtins import owned, array
from guppylang.std.quantum import qubit, measure, cx, discard

test_module = GuppyModule("test")
test_module.load_all(quantum)


@guppy(test_module)
def test(q: qubit @ owned, x: int, b: int) -> int:  # type: ignore
    xs = array(x, 0, 0)
    r = qubit()
    cx(q, r)
    if xs[0] == 0:
        a = measure(q)
        discard(r)
    else:
        a = measure(r)
        discard(q)
    return int(a)
