import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def main(n: int) -> None:
    array(i for i in range(n))


module.compile()
