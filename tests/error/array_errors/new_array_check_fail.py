import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main() -> int:
    return array(1)


module.compile()