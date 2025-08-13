from guppylang.decorator import guppy
from guppylang.std.array import array
from guppylang_internals.tys.ty import UnitaryFlags


@guppy
def test(q: array[int, 3]) -> None:
    with dagger:
        q[0]


test.compile()
