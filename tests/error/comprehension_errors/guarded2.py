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
def foo(qs: linst[tuple[bool, Qubit]]) -> list[int]:
    return [42 for b, q in qs if b if q]


module.compile()
