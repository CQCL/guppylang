import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q1: qubit
    q2: qubit


@guppy.declare(module)
def bar(q: qubit) -> bool:
    ...


@guppy(module)
def foo(qs: linst[MyStruct]) -> linst[qubit]:
    return [s.q2 for s in qs if bar(s.q1)]


module.compile()
