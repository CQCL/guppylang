from guppylang import qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import discard

module = GuppyModule("test")
module.load(qubit, discard)


@guppy.struct(module)
class S:
    x: int
    q: qubit


@guppy.declare(module)
def bar(s: S) -> None: ...


@guppy.comptime(module)
def foo(s: S @ owned) -> None:
    bar(s)
    # Remains immutable after an inout call
    s.x = 1
    discard(s.q)


module.compile()
