from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


def build():
    @guppy.struct(module)
    class Foo:
        x: "blah"


build()
module.compile()
