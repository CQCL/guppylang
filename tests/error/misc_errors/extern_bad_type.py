from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

import guppylang.std.quantum as quantum


module = GuppyModule("test")

guppy.extern("x", ty="float[int]", module=module)

module.compile()
