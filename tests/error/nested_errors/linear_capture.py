import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module
def foo(q: Qubit) -> Qubit:
    def bar() -> Qubit:
        return q

    return q


module.compile(True)
