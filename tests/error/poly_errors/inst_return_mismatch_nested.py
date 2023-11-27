from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: T) -> T:
    ...


@guppy(module)
def main(x: bool) -> None:
    y: None = foo(foo(foo(x)))


module.compile()
