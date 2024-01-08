from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def make() -> T:
    ...


@guppy(module)
def foo(x: T) -> T:
    def bar() -> None:
        y: T = make()

    return x


module.compile()
