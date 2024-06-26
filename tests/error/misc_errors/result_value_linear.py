import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import result
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: qubit) -> None:
    result(0, q)


module.compile()
