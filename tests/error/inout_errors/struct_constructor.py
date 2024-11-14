from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.struct(module)
class MyStruct:
    q: qubit

@guppy(module)
def test(q: qubit) -> MyStruct:
    return MyStruct(q)


module.compile()
