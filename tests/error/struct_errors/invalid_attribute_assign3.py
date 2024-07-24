from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: int
    y: bool


@guppy(module)
def foo(s: MyStruct) -> None:
    s.x, a = (1, 2), 3


module.compile()
