from tests.util import compile_guppy
from guppylang.std.quantum import qubit, x


@compile_guppy
def foo() -> None:
    t = (qubit(), qubit(), 0)
    while True:
        x(t[0])