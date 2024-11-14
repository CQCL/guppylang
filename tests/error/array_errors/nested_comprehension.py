import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main() -> array[int, 50]:
    return array(0 for _ in range(10) for _ in range(5))


module.compile()
