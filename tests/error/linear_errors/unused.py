import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(q: qubit) -> int:
    x = q
    return 42


module.compile()
