import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q1: qubit
    q2: qubit


@guppy(module)
def foo(b: bool, s: MyStruct @owned) -> MyStruct:
    if b:
        measure(s.q2)
    return s


module.compile()
