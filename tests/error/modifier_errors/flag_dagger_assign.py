from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags


@guppy(dagger=True)
def test() -> None:
    x = 3


test.compile()
