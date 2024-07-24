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
def foo(s: MyStruct) -> MyStruct:
    s.q = qubit()
    return s


module.compile()
