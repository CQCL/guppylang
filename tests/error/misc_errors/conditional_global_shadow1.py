from guppylang.decorator import guppy
from guppylang.module import GuppyModule

mod = GuppyModule("test")

@guppy(mod)
def x() -> None:
    pass

@guppy(mod)
def bad(b: bool) -> int:
    if b:
        x = 4
    return x

mod.compile()
