from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


module = GuppyModule("test")
blah = owned


@guppy.declare(module)
def foo(x: int @blah) -> qubit: ...


module.compile()
