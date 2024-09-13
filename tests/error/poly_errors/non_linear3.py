from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule

from guppylang.prelude.quantum import quantum, qubit

module = GuppyModule("test")
module.load_all(quantum)


T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: Callable[[T], None]) -> None:
    ...

@guppy.declare(module)
def h(q: qubit) -> None: ...


@guppy(module)
def main() -> None:
    foo(h)


module.compile()
