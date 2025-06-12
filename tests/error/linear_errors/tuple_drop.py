from tests.util import compile_guppy
from guppylang.std.quantum import qubit

@compile_guppy
def foo() -> qubit:
    return (qubit(), qubit(), qubit())[1]
