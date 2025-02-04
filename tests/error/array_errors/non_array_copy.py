from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

@guppy(module)
def main() -> None:
   y = copy("not an array")

module.compile()
