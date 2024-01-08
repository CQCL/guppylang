from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

S = guppy.type_var(module, "S")
T = guppy.type_var(module, "T")


@guppy(module)
def foo(x: S) -> T:
    return x


module.compile()
