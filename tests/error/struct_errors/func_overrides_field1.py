from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class MyStruct:
    x: int

    @guppy(module)
    def x(self: "MyStruct") -> int:
        return 0


module.compile()
