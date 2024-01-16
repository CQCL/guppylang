from guppylang.decorator import guppy
from guppylang.hugr import tys
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.TupleType(inner=[]))
class MyIter:
    """An iterator that is missing the `__next__` method."""

    @guppy.declare(module)
    def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]:
        ...

    @guppy.declare(module)
    def __end__(self: "MyIter") -> None:
        ...


@guppy.type(module, tys.TupleType(inner=[]))
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
