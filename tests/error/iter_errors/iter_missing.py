from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.tys.ty import NoneType


module = GuppyModule("test")


@guppy.type(NoneType(), module=module)
class MyType:
    """A non-iterable type."""


@guppy(module)
def test(x: MyType) -> None:
    for _ in x:
        pass


module.compile()
