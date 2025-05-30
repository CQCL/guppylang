from guppylang.decorator import guppy
from guppylang.tys.ty import NoneType


@guppy.type(NoneType())
class MyType:
    """A non-iterable type."""


@guppy
def test(x: MyType) -> None:
    for _ in x:
        pass


guppy.compile(test)
