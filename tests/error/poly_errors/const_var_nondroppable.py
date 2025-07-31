from typing import Generic

from hugr import tys

from guppylang.decorator import guppy


@guppy.type(tys.Tuple(), droppable=False)
class MyType:
    pass


X = guppy.const_var("X", "MyType")


@guppy.struct
class Struct(Generic[X]):
    pass


@guppy
def main(_: Struct[X]) -> None:
    pass


main.compile()
