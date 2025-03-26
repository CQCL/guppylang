from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.qsystem import measure

module = GuppyModule("test")
module.load(qubit, measure)


@guppy.comptime(module)
def test() -> int:
    q = qubit()
    if measure(q):
        return 1
    return 0


module.compile()
