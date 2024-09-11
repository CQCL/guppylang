from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import h

import guppylang.prelude.quantum as quantum

module = GuppyModule("test")
module.load_all(quantum)


T = guppy.type_var("T", module=module)


@guppy.declare(module)
def foo(x: Callable[[T], T]) -> None:
    ...


@guppy(module)
def main() -> None:
    foo(h)


module.compile()
