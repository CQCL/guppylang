import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst, owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: linst[tuple[qubit, bool]] @owned) -> linst[qubit]:
    rs: linst[qubit] = []
    for q, b in qs:
        rs += [q]
        if b:
            return []
    return rs


module.compile()
