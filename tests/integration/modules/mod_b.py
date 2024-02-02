from guppylang import GuppyModule, guppy
from guppylang.gtypes import BoolType
from guppylang.hugr import ops

mod_b = GuppyModule("mod_b")


@guppy.declare(mod_b)
def f(x: bool) -> bool:
    ...


@guppy.hugr_op(mod_b, ops.DummyOp(name="dummy"))
def h() -> int:
    ...


@guppy.type(mod_b, BoolType().to_hugr())
class MyType:
    @guppy.declare(mod_b)
    def __pos__(self: "MyType") -> "MyType":
        ...
