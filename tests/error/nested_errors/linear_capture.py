import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(q: qubit @owned) -> qubit:
    def bar() -> qubit:
        return q

    return q


module.compile()
