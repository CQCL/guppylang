import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def bar(q: qubit) -> bool:
    ...


@guppy(module)
def foo(qs: linst[qubit]) -> linst[qubit]:
    return [q for q in qs if bar(q)]


module.compile()
