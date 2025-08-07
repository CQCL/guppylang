from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop


@guppy.struct
class MyStruct[T: (Copy, Drop), x: T]:
    pass


MyStruct.compile()
