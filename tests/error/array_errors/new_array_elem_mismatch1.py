import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main() -> array[int, 1]:
    array(False)


module.compile()