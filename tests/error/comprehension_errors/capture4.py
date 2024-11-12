import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(xs: list[int], s: MyStruct @owned) -> list[qubit]:
    return [s.q for x in xs]


module.compile()
