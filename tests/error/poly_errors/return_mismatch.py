from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo() -> tuple[T, T]:
    ...


@guppy(module)
def main() -> None:
    x: bool = foo()


module.compile()
