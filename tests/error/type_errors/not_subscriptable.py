from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def foo(x: int) -> None:
    x[0]


module.compile()
