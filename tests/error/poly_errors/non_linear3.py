from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

from guppylang.std.quantum import qubit

module = GuppyModule("test")
module.load(qubit)


T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: Callable[[T], None]) -> None:
    ...

@guppy.declare(module)
def h(q: qubit) -> None: ...


@guppy(module)
def main() -> None:
    foo(h)


module.compile()
