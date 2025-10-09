from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, UnitaryFlags
from guppylang.std.array import array


@guppy.with_unitary_flags(UnitaryFlags.Power)
@guppy
def foo(q: qubit) -> None:
    pass


@guppy
def test() -> None:
    q = qubit()
    with dagger:
        with power(2):
            foo(q)


test.compile()
