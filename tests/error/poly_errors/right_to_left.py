from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


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
