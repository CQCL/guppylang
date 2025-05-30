from guppylang.decorator import guppy


@guppy.struct
class MyStruct:
    x: "tuple[MyStruct, int]"


guppy.compile(MyStruct)
