from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.declare(module)
def foo(q: qubit, x: int) -> int: ...


@guppy(module)
def test(q: qubit @owned) -> tuple[int, qubit]:
    # This doesn't work since arguments are evaluated from left to right
    return foo(q, foo(q, foo(q, 0))), q


module.compile()
