from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy(module)
def foo(x: T) -> T:
    def bar() -> None:
        _ = x

    return x


module.compile()
