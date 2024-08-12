from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import measure, qubit, quantum

module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def use(q: qubit) -> None: ...


@guppy(module)
def test(q: qubit @inout, b: bool) -> None:
    if b:
        use(q)


module.compile()
