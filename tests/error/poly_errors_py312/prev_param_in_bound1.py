from guppylang.decorator import guppy
from guppylang.std.lang import Copy, Drop


@guppy
def main[T: (Copy, Drop), x: T]() -> None:
    ...


guppy.compile(main)
