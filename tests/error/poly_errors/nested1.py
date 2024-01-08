from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy(module)
def foo() -> int:
    def bar(x: T) -> T:
        return x

    return bar(42)


module.compile()
