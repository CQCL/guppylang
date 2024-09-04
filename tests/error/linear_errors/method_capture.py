import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.struct(module)
class Struct:
    q: qubit

    @guppy(module)
    def foo(self: "Struct") -> "Struct":
        return self


@guppy(module)
def foo(s: Struct) -> Struct:
    f = s.foo
    return f()


module.compile()
