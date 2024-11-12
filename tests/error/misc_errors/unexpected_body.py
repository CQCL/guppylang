from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

@guppy.declare(module)
def foo() -> int:
    return 42


module.compile()
