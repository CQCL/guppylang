from guppy.compiler import GuppyModule
from tests.error.util import guppy, qubit


module = GuppyModule("test")


@module.declare
def new_qubit() -> qubit:
    pass


@module
def foo(q: qubit) -> tuple[qubit, qubit]:
    q, r = new_qubit(), new_qubit()
    return q, r


module.compile(True)
