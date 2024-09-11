from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit, quantum

module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo(q: qubit) -> None: ...


@guppy(module)
def test() -> None:
   foo(qubit())


module.compile()
