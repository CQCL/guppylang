from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.comptime(module)
def foo() -> None:
    pass


module.compile()

foo()
