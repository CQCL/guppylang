from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.struct(module)
class StructA:
    x: "list[StructB]"


@guppy.struct(module)
class StructB:
    y: "StructA"


module.compile()
