from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.prelude.quantum import Qubit

import guppy.prelude.quantum as quantum

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
