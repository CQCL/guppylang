from guppylang.decorator import guppy
from guppylang.tys.ty import NoneType


@guppy.type(NoneType().to_hugr())
class MyIter:
    """An iterator that is missing the `__next__` method."""

    @guppy.declare
    def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]:
        ...

    @guppy.declare
    def __end__(self: "MyIter") -> None:
        ...


@guppy.type(NoneType().to_hugr())
class MyType:
    """Type that produces the iterator above."""

    @guppy.declare
    def __iter__(self: "MyType") -> MyIter:
        ...


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


guppy.compile(test)
