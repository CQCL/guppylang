from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: T) -> T:
    ...


@guppy(module)
def main(x: bool) -> None:
    y: None = foo(foo(foo(x)))


module.compile()
