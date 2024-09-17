from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def main(x: list[int]) -> list[int]:
    return x


module.compile()
