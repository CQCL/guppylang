from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

@guppy(module)
def main() -> None:
    l = [1, 2, 3]
    l[0] = 3

module.compile()