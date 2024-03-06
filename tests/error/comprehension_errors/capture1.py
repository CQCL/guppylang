import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(xs: list[int], q: qubit) -> linst[qubit]:
    return [q for x in xs]


module.compile()
