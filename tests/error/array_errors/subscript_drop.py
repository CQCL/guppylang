import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy.declare(module)
def foo() -> array[qubit, 10]: ...


@guppy(module)
def main() -> qubit:
    return foo()[0]


module.compile()