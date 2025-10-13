from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned, UnitaryFlags


@guppy.declare
def discard(q: qubit @ owned) -> None: ...


@guppy.with_unitary_flags(UnitaryFlags.Control)
@guppy.declare
def use(q: qubit) -> None: ...


@guppy
def test() -> None:
    q = qubit()
    with control(q):
        use(q)
    discard(q)


test.compile()
