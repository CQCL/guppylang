from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags
from guppylang.std.array import array


@guppy.with_unitary_flags(UnitaryFlags.Dagger)
@guppy
def test() -> None:
    for _ in range(10):
        pass


test.compile()
