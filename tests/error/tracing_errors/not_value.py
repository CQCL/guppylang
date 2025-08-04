from hugr import tys

from guppylang_internals.decorator import guppy, custom_type


@custom_type(tys.Tuple())
class T:
    pass


@guppy.declare
def foo(x: T) -> None: ...


@guppy.comptime
def test() -> None:
    foo(T)


test.compile()
