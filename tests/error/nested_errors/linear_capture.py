import guppy.prelude.quantum as quantum
from guppy.decorator import guppy
from guppy.module import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(quantum)


@guppy(module)
def foo(q: Qubit) -> Qubit:
    def bar() -> Qubit:
        return q

    return q


module.compile()
