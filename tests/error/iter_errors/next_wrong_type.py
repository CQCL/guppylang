from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.tys.ty import NoneType


module = GuppyModule("test")


@guppy.type(NoneType().to_hugr(), module=module)
class MyIter:
    """An iterator where the `__next__` method has the wrong signature."""

    @guppy.declare(module)
    def __next__(self: "MyIter") -> tuple["MyIter", float]:
        ...

    @guppy.declare(module)
    def __hasnext__(self: "MyIter") -> tuple[bool, "MyIter"]:
        ...

    @guppy.declare(module)
    def __end__(self: "MyIter") -> None:
        ...


@guppy.type(NoneType().to_hugr(), module=module)
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
