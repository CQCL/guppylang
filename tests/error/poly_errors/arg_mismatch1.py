from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: T, y: T) -> None:
    ...


@guppy(module)
def main(x: bool, y: tuple[bool]) -> None:
    foo(x, y)


module.compile()
