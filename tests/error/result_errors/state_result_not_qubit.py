from guppylang.std.debug import state_result
from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")
module.load(state_result)

@guppy(module)
def main(x: int) -> None:
    state_result("tag", x)

module.compile()