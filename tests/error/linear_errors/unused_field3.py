import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct1:
    x: "MyStruct2"
    y: int


@guppy.struct(module)
class MyStruct2:
    q1: qubit
    q2: qubit


@guppy(module)
def foo(s: MyStruct1 @owned) -> int:
    measure(s.x.q1)
    return s.y


module.compile()
