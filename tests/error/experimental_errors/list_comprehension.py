from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")


@guppy(module)
def main() -> None:
    [i for i in range(10)]


module.compile()
