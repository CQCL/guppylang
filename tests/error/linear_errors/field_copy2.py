import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)

@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(s: MyStruct @owned) -> tuple[MyStruct, qubit]:
    return s, s.q


module.compile()
