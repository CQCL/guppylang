from guppy.decorator import guppy
from guppy.hugr import tys
from guppy.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.Tuple(inner=[]))
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
