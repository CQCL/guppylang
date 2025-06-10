from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit
from guppylang.std.quantum_functional import h


@guppy
def foo(q: qubit @owned) -> None:
    h(q)


guppy.compile(foo)
