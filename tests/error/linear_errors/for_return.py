import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: list[tuple[qubit, bool]] @owned) -> list[qubit]:
    rs: list[qubit] = []
    for q, b in qs:
        rs += [q]
        if b:
            return []
    return rs


module.compile()
