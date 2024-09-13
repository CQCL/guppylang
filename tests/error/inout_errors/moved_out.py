from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import measure, qubit, quantum

module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class MyStruct:
    q: qubit


@guppy.declare(module)
def use(q: qubit @owned) -> None: ...


@guppy(module)
def test(s: MyStruct) -> None:
    use(s.q)


module.compile()
