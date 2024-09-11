from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import measure, qubit, quantum

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def test(q: qubit) -> qubit:
    r = q
    q = qubit()
    return r


module.compile()
