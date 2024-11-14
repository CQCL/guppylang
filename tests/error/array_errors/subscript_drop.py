import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo() -> array[qubit, 10]: ...


@guppy(module)
def main() -> qubit:
    return foo()[0]


module.compile()