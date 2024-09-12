from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.builtins import owned
from guppylang.prelude.quantum import quantum, qubit


module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def foo() -> qubit @owned: ...


module.compile()
