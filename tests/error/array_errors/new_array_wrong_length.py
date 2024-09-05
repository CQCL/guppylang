import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main() -> array[int, 2]:
    return array(1, 2, 3)


module.compile()
