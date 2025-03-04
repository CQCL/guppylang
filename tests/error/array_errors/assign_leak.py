import guppylang.std.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array
from guppylang.std.quantum import qubit


module = GuppyModule("test")
module.load_all(quantum)

@guppy(module)
def main() -> None:
    qs = array(qubit() for _ in range(10)) 
    qs[0] = qubit()  # Leaks the old qubit at index 0

module.compile()