import guppy.prelude.quantum

from guppy.compiler import GuppyModule
from guppy.hugr.tys import Qubit


module = GuppyModule("test")
module.load(guppy.prelude.quantum)


@module
def foo(q: Qubit) -> int:
    x = q
    return 42


module.compile(True)
