import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array, inout
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo(qs: array[qubit, 42], q: qubit @inout) -> array[qubit, 42]: ...


@guppy(module)
def main(qs: array[qubit, 42]) -> array[qubit, 42]:
    return foo(qs, qs[0])


module.compile()