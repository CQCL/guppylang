from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


@guppy.declare(module)
def foo(q: qubit @inout) -> None: ...


@guppy.struct(module)
class MyImmutableContainer:
    q: qubit

    @guppy.declare(module)
    def __getitem__(self: "MyImmutableContainer" @inout, idx: int) -> qubit: ...


@guppy(module)
def test(c: MyImmutableContainer) -> MyImmutableContainer:
    foo(c[0])
    return c


module.compile()
