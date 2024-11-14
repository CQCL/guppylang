import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q1: qubit
    q2: qubit


@guppy(module)
def foo() -> MyStruct:
    return MyStruct(qubit(), qubit())


@guppy(module)
def bar() -> qubit:
    return foo().q1


module.compile()
