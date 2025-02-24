from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import array


module = GuppyModule("test")

@guppy(module)
def main() -> None:
    a = array(1, 2, 3)
    a[0] = "not an int"

module.compile()