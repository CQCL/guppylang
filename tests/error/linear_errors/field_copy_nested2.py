import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct1:
    x: "MyStruct2"


@guppy.struct(module)
class MyStruct2:
    q1: qubit
    q2: qubit


@guppy(module)
def foo(s: MyStruct1 @owned) -> MyStruct1:
    measure(s.x.q1)
    return MyStruct1(s.x)


module.compile()
