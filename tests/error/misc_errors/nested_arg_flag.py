from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import qubit


module = GuppyModule("test")
module.load(qubit)


@guppy.declare(module)
def foo(x: list[qubit @owned]) -> qubit: ...


module.compile()
