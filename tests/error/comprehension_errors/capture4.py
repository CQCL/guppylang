import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst

module = GuppyModule("test")
module.load(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(xs: list[int], s: MyStruct) -> linst[qubit]:
    return [s.q for x in xs]


module.compile()
