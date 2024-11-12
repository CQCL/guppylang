from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")


@guppy.declare(module)
def foo(x: int @owned) -> qubit: ...


module.compile()
