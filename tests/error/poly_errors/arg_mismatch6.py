from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: T) -> None:
    ...


@guppy(module)
def main(x: float) -> None:
    foo[int](x)


module.compile()
