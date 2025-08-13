from guppylang_internals.tys.ty import UnitaryFlags
from guppylang.decorator import guppy
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: qubit) -> None: ...


@guppy(unitary_flags=UnitaryFlags.Dagger)
def test(x: qubit) -> None:
    foo(x)


test.compile()
