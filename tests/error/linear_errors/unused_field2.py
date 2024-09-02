import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q1: qubit
    q2: qubit


@guppy(module)
def foo(s: MyStruct) -> qubit:
    return s.q1


module.compile()
