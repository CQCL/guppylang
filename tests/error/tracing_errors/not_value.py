from hugr import tys

from guppylang.decorator import guppy


@guppy.type(tys.Tuple())
class T:
    pass


@guppy.declare
def foo(x: T) -> None: ...


@guppy.comptime
def test() -> None:
    foo(T)


test.compile()
