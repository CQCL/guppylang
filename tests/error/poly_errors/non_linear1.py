from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import Qubit

import guppylang.prelude.quantum as quantum

module = GuppyModule("test")
module.load(quantum)


T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: T) -> None:
    ...


@guppy(module)
def main(q: Qubit) -> None:
    foo(q)


module.compile()
