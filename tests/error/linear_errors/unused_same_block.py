import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module
def foo(q: Qubit) -> int:
    x = q
    x = 10
    return x


module.compile(True)
