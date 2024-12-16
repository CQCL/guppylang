import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit
from guppylang.std.builtins import owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def bar(q: qubit) -> list[qubit]: ...


@guppy(module)
def foo(qs: list[qubit] @owned) -> list[qubit]:
    return [r for q in qs for r in bar(q)]


module.compile()
