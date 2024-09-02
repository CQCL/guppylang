"""Dummy module used in `test_imports.py`"""

from guppylang import GuppyModule, guppy
from guppylang.prelude._internal.util import int_op

mod_b = GuppyModule("mod_b")


@guppy(mod_b)
def f(x: bool) -> bool:
    return not x


@guppy.hugr_op(mod_b, int_op("h", "dummy", 0))
def h() -> int:
    ...


@guppy.struct(mod_b)
class MyType:
    x: int

    @guppy(mod_b)
    def __pos__(self: "MyType") -> "MyType":
        return self
