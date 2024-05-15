from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


x = 42


@guppy.struct(module)
class MyStruct:
    x


module.compile()
