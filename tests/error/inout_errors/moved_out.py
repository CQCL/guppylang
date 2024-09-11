from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy.declare(module)
def use(q: qubit) -> None: ...


@guppy(module)
def test(s: MyStruct @inout) -> None:
    use(s.q)


module.compile()
