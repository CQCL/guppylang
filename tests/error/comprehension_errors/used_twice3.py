import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit
from guppy.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def bar(q: Qubit) -> list[int]:
    ...


@guppy(module)
def foo(qs: linst[Qubit]) -> linst[Qubit]:
    return [q for q in qs for x in bar(q)]


module.compile()
