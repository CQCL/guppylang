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
def foo(i: int) -> bool:
    b = False
    while i > 0:
        q = new_qubit()
        if i % 10 == 0:
            break
        i -= 1
        b &= measure(q)
    return b


module.compile()
