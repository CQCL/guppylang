from hugr import tys

from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.type(tys.Tuple(), module=module)
class T:
    pass


@guppy.declare(module)
def foo(x: T) -> None: ...


@guppy.comptime(module)
def test() -> None:
    foo(T)


module.compile()
