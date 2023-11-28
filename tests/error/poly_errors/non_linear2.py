from typing import Callable

from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.prelude.quantum import h

import guppy.prelude.quantum as quantum

module = GuppyModule("test")
module.load(quantum)


T = guppy.type_var(module, "T")


@guppy.declare(module)
def foo(x: Callable[[T], T]) -> None:
    ...


@guppy(module)
def main() -> None:
    foo(h)


module.compile()
