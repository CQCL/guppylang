from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit

import guppylang.prelude.quantum as quantum


module = GuppyModule("test")

guppy.extern(module, "x", ty="float[int]")

module.compile()
