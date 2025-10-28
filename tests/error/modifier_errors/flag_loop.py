from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags
from guppylang.std.array import array


@guppy(dagger=True)
def test() -> None:
    for _ in range(10):
        pass


test.compile()
