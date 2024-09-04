import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: linst[tuple[qubit, qubit]]) -> linst[qubit]:
    return [q for q, q in qs]


module.compile()
