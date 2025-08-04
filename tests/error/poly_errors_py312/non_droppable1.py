from hugr import tys

from guppylang_internals.decorator import guppy, custom_type


@custom_type(tys.Tuple(), droppable=False)
class NonDroppable:
    pass


@guppy
def main[D: NonDroppable]() -> None:
    pass


main.compile()
