from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array

module = GuppyModule("test")


@guppy.declare(module)
def foo(xs: array[int, 0]) -> None: ...


@guppy.comptime(module)
def test(xs: array[int, 0]) -> None:
    foo(xs)  # This works
    foo([])  # But we currently cannot infer the type here


module.compile()
