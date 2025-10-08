from guppylang.decorator import guppy
from guppylang.std.quantum import qubit, owned, UnitaryFlags


@guppy.declare(unitary_flags=UnitaryFlags.Dagger)
def discard(q: qubit @ owned) -> None: ...


# TODO: The error message is not prefect.
@guppy
def test() -> None:
    a = qubit()
    with dagger:
        discard(a)


test.compile()
