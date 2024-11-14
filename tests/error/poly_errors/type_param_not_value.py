from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy(module)
def foo(x: T) -> None:
    y = T


module.compile()
