from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x = 42


module.compile()
