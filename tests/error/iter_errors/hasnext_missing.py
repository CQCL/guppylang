from guppy.decorator import guppy
from guppy.hugr import tys
from guppy.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.Tuple(inner=[]))
class MyIter:
    """An iterator that is missing the `__hasnext__` method."""

    @guppy.declare(module)
    def __next__(self: "MyIter") -> tuple[None, "MyIter"]:
        ...

    @guppy.declare(module)
    def __end__(self: "MyIter") -> None:
        ...


@guppy.type(module, tys.Tuple(inner=[]))
class MyType:
    """Type that produces the iterator above."""

    @guppy.declare(module)
    def __iter__(self: "MyType") -> MyIter:
        ...


@guppy(module)
def test(x: MyType) -> None:
    for _ in x:
        pass


module.compile()
