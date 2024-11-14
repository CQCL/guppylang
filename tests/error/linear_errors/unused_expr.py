from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit
from guppylang.std.quantum_functional import h

module = GuppyModule("test")
module.load(qubit, h)


@guppy(module)
def foo(q: qubit @owned) -> None:
    h(q)


module.compile()
