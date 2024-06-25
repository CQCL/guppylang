from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy(module)
def main(x: list[42]) -> None:
    pass


module.compile()
