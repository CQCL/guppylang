from typing import Generic, TypeVar

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


X = TypeVar("X")  # This is a Python type variable, not a Guppy one!


@guppy.struct(module)
class MyStruct(Generic[X]):
    x: int


module.compile()
