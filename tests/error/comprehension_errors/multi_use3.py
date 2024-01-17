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
def foo(qs: linst[Qubit], xs: list[int]) -> list[int]:
    return [x for q in qs for x in xs if bar(q)]


module.compile()
