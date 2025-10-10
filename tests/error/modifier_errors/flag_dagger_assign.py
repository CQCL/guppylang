from guppylang.decorator import guppy
from guppylang.std.quantum import UnitaryFlags


@guppy.with_unitary_flags(UnitaryFlags.Dagger)
@guppy
def test() -> None:
    x = 3


test.compile()
