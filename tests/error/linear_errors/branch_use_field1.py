import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit, measure


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(b: bool) -> bool:
    s = MyStruct(qubit())
    if b:
        return measure(s.q)
    return False


module.compile()
