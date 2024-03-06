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
def foo(q: qubit) -> qubit:
    q = new_qubit()
    return q


module.compile()
