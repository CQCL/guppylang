from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")

@guppy.declare(module)
def foo() -> array[int, 10]: ...

@guppy(module)
def main() -> None:
    foo()[0] = 22

module.compile()