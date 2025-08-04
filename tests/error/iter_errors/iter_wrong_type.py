from guppylang.decorator import guppy
from guppylang.tys.ty import NoneType


@guppy.type(lambda _, ctx: NoneType().to_hugr(ctx))
class MyType:
    """A type where the `__iter__` method has the wrong signature."""

    @guppy.declare
    def __iter__(self: "MyType", x: int) -> "MyType":
        ...


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


test.compile()
