from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit, quantum

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def foo(q: qubit @inout) -> None: ...


@guppy(module)
def test(q: qubit) -> None:
   foo(q)


module.compile()
