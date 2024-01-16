from guppy.decorator import guppy
from guppy.hugr import tys
from guppy.module import GuppyModule


module = GuppyModule("test")


@guppy.type(module, tys.TupleType(inner=[]))
class MyType:
    """A non-iterable type."""


@guppy(module)
def test(x: MyType) -> None:
    for _ in x:
        pass


module.compile()
