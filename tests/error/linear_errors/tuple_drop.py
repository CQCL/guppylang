from tests.util import compile_guppy
from guppylang.std.quantum import qubit
from guppylang.std.builtins import array

@compile_guppy
def foo() -> qubit:
    return (1, qubit(), array(1, 2))[1]
