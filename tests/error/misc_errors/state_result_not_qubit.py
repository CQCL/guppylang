from guppylang.std.builtins import state_result
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")

@guppy(module)
def main(x: int) -> None:
    state_result("tag", x)

module.compile()