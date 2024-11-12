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


@guppy.declare(module)
def measure(q: qubit @owned) -> bool:
    ...


@guppy(module)
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


module.compile()
