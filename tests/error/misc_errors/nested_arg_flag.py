from guppylang.decorator import guppy
from guppylang.std.builtins import owned
from guppylang.std.quantum import qubit


@guppy.declare
def foo(x: list[qubit @owned]) -> qubit: ...


guppy.compile(foo)
