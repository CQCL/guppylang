import guppylang.prelude.quantum as quantum
from guppylang.decorator import guppy
from guppylang.module import GuppyModule
from guppylang.prelude.quantum import qubit
from guppylang.prelude.builtins import linst, owned

module = GuppyModule("test")
module.load_all(quantum)


@guppy.declare(module)
def bar(q: qubit @owned) -> bool:
    ...


@guppy(module)
def foo(xs: list[int], q: qubit @owned) -> list[int]:
    return [x for x in xs if bar(q)]


module.compile()
