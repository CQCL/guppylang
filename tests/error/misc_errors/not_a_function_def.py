from guppylang.decorator import guppy
from guppylang.module import GuppyModule

module = GuppyModule("test")

f = lambda x: x
guppy(module)(f)

module.compile()
