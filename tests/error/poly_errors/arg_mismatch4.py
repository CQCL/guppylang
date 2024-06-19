from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy(module)
def main(x: "array[int, bool]") -> None:
    pass


module.compile()
