import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q1: qubit
    q2: qubit


@guppy.declare(module)
def bar(q: qubit @owned) -> bool:
    ...


@guppy(module)
def foo(qs: list[MyStruct] @owned) -> list[qubit]:
    return [s.q2 for s in qs if bar(s.q1)]


module.compile()
