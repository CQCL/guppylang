from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class S:
    x: int


@guppy.comptime(module)
def foo(s: S) -> None:
    s.x = 1


@guppy.comptime(module)
def main() -> None:
    s = S(0)
    foo(s)
    # Python users would expect s to be mutated by the call above. However, we cannot
    # provide this semantics, so the mutation in `foo` is rejected by the compiler.


module.compile()
