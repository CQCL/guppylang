import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit
from guppy.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(qs: linst[Qubit], xs: list[int]) -> linst[Qubit]:
    return [q for q in qs for q in xs]


module.compile()
