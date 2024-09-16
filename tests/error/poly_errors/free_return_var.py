from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo() -> T:
    ...


@guppy(module)
def main() -> None:
    x = foo()


module.compile()
