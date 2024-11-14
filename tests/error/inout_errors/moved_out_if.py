from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy.declare(module)
def use(q: qubit @owned) -> None: ...


@guppy(module)
def test(s: MyStruct, b: bool) -> None:
    if b:
        use(s.q)


module.compile()
