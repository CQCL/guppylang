import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: linst[qubit], xs: list[int]) -> linst[qubit]:
    return [q for q in qs for x in xs]


module.compile()
