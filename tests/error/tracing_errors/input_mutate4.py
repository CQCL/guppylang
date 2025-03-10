from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned

module = GuppyModule("test")


@guppy.struct(module)
class S:
    xs: array[int, 1]


@guppy.comptime(module)
def foo(s: S @ owned) -> None:
    s.xs.clear()


@guppy.comptime(module)
def main() -> None:
    s = S([0])
    foo(s)
    # Python users would expect s to be mutated by the call above. However, we cannot
    # provide this semantics, so the mutation in `foo` is rejected by the compiler.


module.compile()
