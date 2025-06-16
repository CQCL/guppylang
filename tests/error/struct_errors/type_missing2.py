from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x = 42


guppy.compile(MyStruct)
