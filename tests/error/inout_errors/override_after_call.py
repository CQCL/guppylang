from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit, quantum

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def foo(q1: qubit @inout, q2: qubit) -> qubit: ...


@guppy(module)
def test(q1: qubit, q2: qubit) -> tuple[qubit, qubit]:
    q1 = foo(q1, q2)
    return q1, q2


module.compile()
