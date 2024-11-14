from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.quantum import qubit

import guppylang.std.quantum as quantum

module = GuppyModule("test")
module.load_all(quantum)


T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: T) -> None:
    ...


@guppy(module)
def main(q: qubit) -> None:
    foo(q)


module.compile()
