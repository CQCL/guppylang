from guppylang_internals.tys.ty import UnitaryFlags
from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned


@guppy.declare
def discard(q: qubit @ owned) -> None: ...


@guppy.declare(unitary_flags=UnitaryFlags.Control)
def use(q: qubit) -> None: ...


@guppy
def test() -> None:
    q = qubit()
    with control(q):
        use(q)
    discard(q)


test.compile()
