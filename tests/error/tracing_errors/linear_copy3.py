from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit, cx

module = GuppyModule("test")
module.load(qubit, cx)


@guppy.comptime(module)
def test() -> qubit:
    q = qubit()
    cx(q, q)
    return q


module.compile()
