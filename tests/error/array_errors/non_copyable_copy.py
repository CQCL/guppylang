import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array, owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)

@guppy(module)
def main(xs: array[qubit, 2] @ owned) -> array[int, 2]:
   ys = copy(xs)
   return ys

module.compile()
