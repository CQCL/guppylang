from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def main() -> None:
    [1, 2, 3]


module.compile()
