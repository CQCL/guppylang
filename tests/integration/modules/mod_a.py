"""Dummy module used in `test_imports.py`"""

import hugr.tys as ht
from guppylang import guppy
from guppylang_internals.decorator import custom_type


@guppy
def f(x: int) -> int:
    return x + 1


@guppy.declare
def g() -> int: ...


@custom_type(ht.Bool)
class MyType:
    @guppy.declare
    def __neg__(self: "MyType") -> "MyType": ...
