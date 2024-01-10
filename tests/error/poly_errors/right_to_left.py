from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo() -> T:
    ...


@guppy.declare(module)
def bar(x: T, y: T) -> None:
    ...


@guppy(module)
def main() -> None:
    bar(foo(), 42)


module.compile()
