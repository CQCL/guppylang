from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

module = GuppyModule("test")


@guppy.comptime(module)
def foo(xs: array[array[int, 1], 1] @ owned) -> None:
    xs[0].insert(1, 0)


@guppy.comptime(module)
def main() -> None:
    xs = [[0]]
    foo(xs)
    # Python users would expect xs to be mutated by the call above. However, we cannot
    # provide this semantics, so the mutation in `foo` is rejected by the compiler.


module.compile()
