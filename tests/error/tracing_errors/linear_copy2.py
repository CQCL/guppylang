from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit, cx

module = GuppyModule("test")
module.load(qubit, cx)


@guppy.comptime(module)
def test(q: qubit) -> None:
    r = q
    cx(q, r)


module.compile()
