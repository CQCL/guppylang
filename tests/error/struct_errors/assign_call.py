from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: int
    y: bool


@guppy(module)
def foo() -> MyStruct:
    return MyStruct(42, False)


@guppy(module)
def bar() -> None:
    foo().x += 1


module.compile()
