from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import array

module = GuppyModule("test")


@guppy(module)
def main(x: array[int, bool]) -> None:
    pass


module.compile()
