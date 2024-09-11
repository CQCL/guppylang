from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy(module)
def test(q: qubit @inout) -> qubit:
    r = q
    q = qubit()
    return r


module.compile()
