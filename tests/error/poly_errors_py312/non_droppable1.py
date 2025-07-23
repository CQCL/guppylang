from hugr import tys

from guppylang.decorator import guppy


@guppy.type(tys.Tuple(), droppable=False)
class NonDroppable:
    pass


@guppy
def main[D: NonDroppable]() -> None:
    pass


guppy.compile(main)
