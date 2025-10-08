from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags


@guppy(unitary_flags=UnitaryFlags.Dagger)
def test() -> None:
    x = 3


test.compile()
