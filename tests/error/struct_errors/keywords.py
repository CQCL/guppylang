from guppylang.decorator import guppy


@guppy.struct
class MyStruct(metaclass=type):
    x: int


guppy.compile(MyStruct)
