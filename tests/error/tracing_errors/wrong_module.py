from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module1 = GuppyModule("module1")
module2 = GuppyModule("module2")


@guppy.declare(module1)
def foo() -> int: ...


@guppy.comptime(module2)
def main() -> int:
    return foo()


module2.compile()
