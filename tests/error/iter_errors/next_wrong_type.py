from guppylang.decorator import guppy
from guppylang.tys.ty import NoneType


@guppy.type(lambda _, ctx: NoneType().to_hugr(ctx))
class MyIter:
    """An iterator where the `__next__` method has the wrong signature."""

    @guppy.declare
    def __next__(self: "MyIter") -> tuple["MyIter", float]:
        ...

    @guppy.declare
    def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]:
        ...

    @guppy.declare
    def __end__(self: "MyIter") -> None:
        ...


@guppy.type(lambda _, ctx: NoneType().to_hugr(ctx))
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
