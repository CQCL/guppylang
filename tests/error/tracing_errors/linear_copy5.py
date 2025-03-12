from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit, cx

module = GuppyModule("test")
module.load(qubit, cx)


@guppy.comptime(module)
def test(qs: array[qubit, 10]) -> None:
    cx(qs[0], qs[0])


module.compile()
