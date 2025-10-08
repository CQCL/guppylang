from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags
from guppylang.std.array import array


@guppy.with_unitary_flags(UnitaryFlags.Dagger)
@guppy
def test() -> None:
    while True:
        pass


test.compile()
