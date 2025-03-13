from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")

S = guppy.type_var("S", module=module)
T = guppy.type_var("T", module=module)
U = guppy.type_var("U", module=module)


@guppy.declare(module)
def foo(x: int) -> None:
    ...


@guppy(module)
def main() -> None:
    foo[int](0)


module.compile()
