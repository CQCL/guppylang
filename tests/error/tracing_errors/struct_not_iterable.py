from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy.struct(module)
class S:
    x: int

    @guppy.declare(module)
    def __iter__(self: "S") -> int: ...


@guppy.comptime(module)
def test() -> None:
    s = S(1)
    s.x = 1.0
    # Even though `S` implements `__iter__`, we can't use it during tracing
    for _ in s:
        pass


module.compile()
