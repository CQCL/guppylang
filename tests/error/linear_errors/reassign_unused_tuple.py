import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def new_qubit() -> qubit:
    ...


@guppy(module)
def foo(q: qubit @owned) -> tuple[qubit, qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile()
