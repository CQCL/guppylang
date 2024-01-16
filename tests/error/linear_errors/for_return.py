import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.hugr.tys import Qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(qs: linst[tuple[Qubit, bool]]) -> linst[Qubit]:
    rs: linst[Qubit] = []
    for q, b in qs:
        rs += [q]
        if b:
            return []
    return rs


module.compile()
