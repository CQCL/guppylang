from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import inout
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")


@guppy.declare(module)
def foo(x: int @inout) -> qubit: ...


module.compile()
