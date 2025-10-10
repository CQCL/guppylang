from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, UnitaryFlags


@guppy.declare
def foo(x: qubit) -> None: ...


@guppy.with_unitary_flags(UnitaryFlags.Dagger)
@guppy
def test(x: qubit) -> None:
    foo(x)


test.compile_function()
