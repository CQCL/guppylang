from guppylang_internals.tys.ty import UnitaryFlags
from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare(unitary_flags=UnitaryFlags.Dagger)
def use(q: qubit) -> None: ...


@guppy
def test() -> None:
    a = qubit()
    with dagger:
        use(a)


test.compile()
