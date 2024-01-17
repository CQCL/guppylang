import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.hugr.tys import Qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def bar(q: Qubit) -> bool:
    ...


@guppy(module)
def foo(qs: linst[tuple[bool, Qubit]]) -> list[int]:
    return [42 for b, q in qs if b if q]


module.compile()
