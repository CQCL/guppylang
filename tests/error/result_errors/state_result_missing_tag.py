from guppylang.std.debug import state_result
from guppylang.std.quantum import discard, qubit
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")
module.load(qubit, discard, state_result)

@guppy(module)
def main() -> None:
    q1 = qubit()
    state_result(q1)
    discard(q1)

module.compile()