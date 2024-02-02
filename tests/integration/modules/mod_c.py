from guppylang import GuppyModule, guppy
from tests.integration.modules.mod_a import mod_a, MyType

mod_c = GuppyModule("mod_c")
mod_c.import_(mod_a, "MyType")


@guppy.declare(mod_c)
def g() -> MyType:
    ...


@guppy.extend_type(mod_c, MyType)
class _:
    @guppy(mod_c)
    def __int__(self: "MyType") -> int:
        return 0
