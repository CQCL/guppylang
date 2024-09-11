from guppylang import GuppyModule, guppy
from tests.integration.modules.mod_a import f, mod_a, MyType

mod_c = GuppyModule("mod_c")
mod_c.load_all(mod_a)


@guppy.declare(mod_c)
def g() -> MyType:
    ...


@guppy(mod_c)
def h(x: int) -> int:
    return f(x)


# Extend type defined in module A
@guppy.extend_type(MyType, module=mod_c)
class _:
    @guppy(mod_c)
    def __int__(self: "MyType") -> int:
        return 0
