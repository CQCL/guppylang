from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.comptime(module)
def test() -> None:
    q = qubit()


module.compile()
