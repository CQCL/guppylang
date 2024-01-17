from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy(module)
def main(x: T) -> T:
    return x


module.compile()
