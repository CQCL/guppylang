import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit
from guppy.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def bar(q: Qubit) -> bool:
    ...


@guppy(module)
def foo(xs: list[int], q: Qubit) -> list[int]:
    return [x for x in xs if bar(q)]


module.compile()
