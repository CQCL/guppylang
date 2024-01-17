from guppylang.decorator import guppy
from guppylang.hugr import tys
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.TupleType(inner=[]))
class MyType:
    """A non-iterable type."""


@guppy(module)
def test(x: MyType) -> None:
    for _ in x:
        pass


module.compile()
