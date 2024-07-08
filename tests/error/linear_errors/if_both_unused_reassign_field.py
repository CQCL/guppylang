import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(b: bool, s: MyStruct) -> MyStruct:
    if b:
        s.q = qubit()
    else:
        s.q = qubit()
    s.q = qubit()
    return s


module.compile()
