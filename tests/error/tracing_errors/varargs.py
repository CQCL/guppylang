from guppylang import guppy
from guppylang.std.quantum import qubit, h, discard_array
from guppylang.std.builtins import array, barrier

@guppy.comptime
def main() -> None:
    qs = array(qubit() for _ in range(5))
    barrier(qs)
    h(qs[0])
    discard_array(qs)

main.compile()
