from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: tuple[T, T]) -> None:
    ...


@guppy(module)
def main() -> None:
    foo(False)


module.compile()
