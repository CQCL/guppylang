from typing import Generic

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")
T = guppy.type_var("T", module=module)


@guppy.struct(module)
class MyStruct(Generic[T]):
    x: T
    y: T


@guppy(module)
def main() -> None:
    MyStruct(0, False)


module.compile()
