from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags


@guppy(unitary_flags=UnitaryFlags.Dagger)
def test() -> None:
    for _ in range(3):
        pass


test.compile()
