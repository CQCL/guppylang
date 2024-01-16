import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit
from guppy.prelude.builtins import linst

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
