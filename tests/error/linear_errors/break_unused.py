import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit


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
    while True:
        q = new_qubit()
        if i == 0:
            break
        i -= 1
        b &= measure(q)
    return b


module.compile()
