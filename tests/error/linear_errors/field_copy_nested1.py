import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct1:
    q: qubit
    x: "MyStruct2"


@guppy.struct(module)
class MyStruct2:
    q: qubit


@guppy(module)
def foo(s: MyStruct1) -> MyStruct1:
    measure(s.q)
    s.q = s.x.q
    return s


module.compile()
