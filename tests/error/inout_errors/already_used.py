from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import measure, qubit, quantum

module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo(q1: qubit) -> None: ...


@guppy.declare(module)
def use(q: qubit @owned) -> None: ...


@guppy(module)
def test(q: qubit @owned) -> None:
    use(q)
    foo(q)


module.compile()
