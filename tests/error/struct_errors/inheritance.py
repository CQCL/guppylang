from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class MyStruct(int):
    x: bool


module.compile()
