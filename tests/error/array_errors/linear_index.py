import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main(qs: array[qubit, 42]) -> int:
    return qs[0]


module.compile()