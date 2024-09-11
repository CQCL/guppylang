from typing import Callable

from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import quantum, qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo(f: "Callable[[], qubit]") -> None: ...


module.compile()
