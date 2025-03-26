from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit, measure

module = GuppyModule("test")
module.load(qubit, measure)


@guppy.comptime(module)
def test(q: qubit) -> None:
    measure(q)


module.compile()
