from guppylang import guppy
from tests.integration.modules.mod_a import f, MyType


@guppy.declare
def g() -> MyType: ...


@guppy
def h(x: int) -> int:
    return f(x)


# Extend type defined in module A
@guppy.extend_type(MyType)
class _:
    @guppy
    def __int__(self: "MyType") -> int:
        return 0
