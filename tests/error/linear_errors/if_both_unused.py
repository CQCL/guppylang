import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def new_qubit() -> qubit:
    ...


@guppy(module)
def foo(b: bool) -> int:
    if b:
        q = new_qubit()
    else:
        q = new_qubit()
    return 42


module.compile()
