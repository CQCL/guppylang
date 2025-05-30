from guppylang.decorator import guppy


@guppy.struct
class MyStruct(int):
    x: bool


guppy.compile(MyStruct)
