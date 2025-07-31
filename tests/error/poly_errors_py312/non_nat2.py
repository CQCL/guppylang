from guppylang.decorator import guppy


@guppy.struct
class MyStruct[I: bool]:
    pass


MyStruct.compile()
