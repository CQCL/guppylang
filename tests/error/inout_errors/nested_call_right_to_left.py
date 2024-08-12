from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit, quantum

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def foo(q: qubit @inout, x: int) -> int: ...


@guppy(module)
def test(q: qubit) -> tuple[int, qubit]:
    # This doesn't work since arguments are evaluated from left to right
    return foo(q, foo(q, foo(q, 0))), q


module.compile()
