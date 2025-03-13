from guppylang.decorator import guppy
from guppylang.module import GuppyModule

mod = GuppyModule("test")

x = guppy.extern("x", ty="int", module=mod)

@guppy(mod)
def bad(b: bool) -> int:
    if b:
        x = 4
    return x

mod.compile()
