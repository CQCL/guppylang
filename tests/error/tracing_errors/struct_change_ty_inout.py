from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")
module.load(qubit)


@guppy.struct(module)
class S:
    x: int
    q: qubit


@guppy.comptime(module)
def test(s: S) -> None:
    s.x = 1.0


module.compile()
