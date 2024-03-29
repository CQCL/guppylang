import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def new_qubit() -> qubit:
    ...


@guppy(module)
def foo(q: qubit) -> tuple[qubit, qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile()
