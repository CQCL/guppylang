from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")

T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: T) -> None:
    ...


@guppy(module)
def main() -> None:
    foo[int, float, bool]


module.compile()
