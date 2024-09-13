from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
blah = owned


@guppy.declare(module)
def foo(x: int @blah) -> qubit: ...


module.compile()
