"""Dummy module used in `test_imports.py`"""

import hugr.tys as ht

from guppylang import GuppyModule, guppy

mod_a = GuppyModule("mod_a")


@guppy(mod_a)
def f(x: int) -> int:
    return x + 1


@guppy.declare(mod_a)
def g() -> int: ...


@guppy.type(ht.Bool, module=mod_a)
class MyType:
    @guppy.declare(mod_a)
    def __neg__(self: "MyType") -> "MyType": ...
