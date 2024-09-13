from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit, quantum

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit

@guppy(module)
def test(q: qubit) -> MyStruct:
    return MyStruct(q)


module.compile()
