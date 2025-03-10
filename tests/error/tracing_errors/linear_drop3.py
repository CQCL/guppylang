from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned, array
from guppylang.std.quantum import qubit, measure

module = GuppyModule("test")
module.load(qubit, measure)


@guppy.comptime(module)
def test(qs: array[qubit, 10] @ owned) -> None:
    for i in range(9):
        measure(qs[i])


module.compile()
