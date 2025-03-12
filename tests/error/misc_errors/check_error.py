from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")


@guppy(module)
def foo(x: float) -> int:
    return x


# Call check instead of compile
module.check()
