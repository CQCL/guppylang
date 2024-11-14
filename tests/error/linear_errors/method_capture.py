import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class Struct:
    q: qubit

    @guppy(module)
    def foo(self: "Struct @owned") -> "Struct":
        return self


@guppy(module)
def foo(s: Struct @owned) -> Struct:
    f = s.foo
    return f()


module.compile()
