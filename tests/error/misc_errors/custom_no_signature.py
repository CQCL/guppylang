from guppylang.decorator import guppy
from guppylang.module import GuppyModule


module = GuppyModule("test")

@guppy.custom(module=module)
def foo(x): ...


module.compile()
