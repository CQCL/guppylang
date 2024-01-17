from guppylang.decorator import guppy
from guppylang.hugr import tys
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.TupleType(inner=[]))
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
