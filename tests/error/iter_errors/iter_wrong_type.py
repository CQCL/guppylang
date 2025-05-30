from guppylang.decorator import guppy
from guppylang.tys.ty import NoneType


@guppy.type(NoneType().to_hugr())
class MyType:
    """A type where the `__iter__` method has the wrong signature."""

    @guppy.declare
    def __iter__(self: "MyType", x: int) -> "MyType":
        ...


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


guppy.compile(test)
