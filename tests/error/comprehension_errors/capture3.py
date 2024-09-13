import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst, owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(xs: list[int], s: MyStruct @owned) -> linst[MyStruct]:
    return [s for x in xs]


module.compile()
