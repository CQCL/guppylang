import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def main(qs: array[qubit, 42]) -> tuple[qubit, array[qubit, 42]]:
    q = qs[0]
    return q, qs


module.compile()