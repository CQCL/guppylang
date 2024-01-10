from guppy.decorator import guppy
from guppy.module import GuppyModule


module = GuppyModule("test")

T = guppy.type_var(module, "T")


@guppy(module)
def main(x: T) -> T:
    return x


module.compile()
