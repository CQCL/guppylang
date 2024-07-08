import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit, measure


module = GuppyModule("test")
module.load(quantum)


@guppy.struct(module)
class MyStruct1:
    x: "MyStruct2"
    y: int


@guppy.struct(module)
class MyStruct2:
    q1: qubit
    q2: qubit


@guppy(module)
def foo(s: MyStruct1) -> int:
    measure(s.x.q1)
    return s.y


module.compile()
