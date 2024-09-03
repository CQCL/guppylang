from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("lib")


@guppy.struct(module)
class MyType:
    x: int


@guppy(module)
def foo(x: int) -> int:
    return x
