from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.declare(module)
def foo(q: qubit) -> None: ...


@guppy(module)
def test() -> None:
   foo(qubit())


module.compile()
