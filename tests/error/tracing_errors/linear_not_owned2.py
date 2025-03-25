from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, measure

module = GuppyModule("test")
module.load(qubit, measure)


@guppy.comptime(module)
def test(qs: array[qubit, 10]) -> None:
    measure(qs[0])


module.compile()
