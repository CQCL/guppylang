from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


def build():
    @guppy(module)
    def foo(x: float) -> int:
        return x


build()
module.compile()
