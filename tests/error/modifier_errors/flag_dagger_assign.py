from guppylang_internals.tys.ty import UnitaryFlags
from guppylang.decorator import guppy


@guppy(unitary_flags=UnitaryFlags.Dagger)
def test() -> None:
    x = 3


test.compile()
