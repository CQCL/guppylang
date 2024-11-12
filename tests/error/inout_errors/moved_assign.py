from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy(module)
def test(q: qubit) -> qubit:
    r = q
    q = qubit()
    return r


module.compile()
