from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.declare(module)
def foo(q1: qubit) -> None: ...


@guppy.declare(module)
def use(q: qubit @owned) -> None: ...


@guppy(module)
def test(q: qubit) -> None:
    foo(q)
    use(q)


module.compile()
