from guppylang import GuppyModule, guppy
from guppylang.gtypes import BoolType

mod_a = GuppyModule("mod_a")


@guppy(mod_a)
def f(x: int) -> int:
    return x


@guppy.declare(mod_a)
def g() -> int:
    ...


@guppy.type(mod_a, BoolType().to_hugr())
class MyType:
    @guppy.declare(mod_a)
    def __neg__(self: "MyType") -> "MyType":
        ...
