from typing import Generic, TypeVar

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")
T = guppy.type_var("T", module=module)


@guppy.struct(module)
class MyStruct(Generic[T]):
    x: list[T]


@guppy(module)
def foo(s: MyStruct[int, bool]) -> None:
    pass


module.compile()
