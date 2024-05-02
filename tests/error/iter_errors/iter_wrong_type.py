from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.tys.ty import NoneType


module = GuppyModule("test")


@guppy.type(module, NoneType().to_hugr())
class MyType:
    """A type where the `__iter__` method has the wrong signature."""

    @guppy.declare(module)
    def __iter__(self: "MyType", x: int) -> "MyType":
        ...


@guppy(module)
def test(x: MyType) -> None:
    for _ in x:
        pass


module.compile()
