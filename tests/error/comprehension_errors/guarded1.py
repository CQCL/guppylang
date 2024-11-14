import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: list[tuple[bool, qubit]] @owned) -> list[qubit]:
    return [q for b, q in qs if b]


module.compile()
