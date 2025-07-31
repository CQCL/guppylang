from hugr import tys

from guppylang.decorator import guppy


@guppy.type(tys.Tuple(), droppable=False)
class NonDroppable:
    pass


@guppy.struct
class MyStruct[D: NonDroppable]:
    pass


MyStruct.compile()
