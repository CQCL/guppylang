import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)

@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy(module)
def foo(s: MyStruct @owned) -> tuple[qubit, MyStruct]:
    return s.q, s


module.compile()
