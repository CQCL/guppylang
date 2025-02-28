from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit, h, measure

module = GuppyModule("test")
module.load(qubit, h, measure)


@guppy.comptime(module)
def test() -> None:
    q = qubit()
    measure(q)
    h(q)


module.compile()
