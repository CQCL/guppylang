import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst, owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy(module)
def foo(qs: linst[qubit] @owned) -> list[int]:
    return [42 for q in qs]


module.compile()
