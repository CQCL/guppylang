from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: int
    x: bool


guppy.compile(MyStruct)
