from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy(module)
def test(q: qubit, b: bool) -> None:
    if b:
        q = qubit()


module.compile()
