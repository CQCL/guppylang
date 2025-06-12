from guppylang import guppy
from tests.util import compile_guppy
from guppylang.std.quantum import qubit, discard
from guppylang.std.builtins import owned

@guppy
def use(x: qubit @ owned) -> qubit:
    return x

@compile_guppy
def foo() -> None:
    t = (qubit(), qubit(), qubit())
    use(t[1])
    discard(t[0])
    discard(t[2])
