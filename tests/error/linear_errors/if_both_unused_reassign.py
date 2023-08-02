from guppy.compiler import GuppyModule
from tests.error.util import guppy, qubit


module = GuppyModule("test")


@module.declare
def new_qubit() -> qubit:
    pass


@module
def foo(b: bool) -> qubit:
    if b:
        q = new_qubit()
    else:
        q = new_qubit()
    q = new_qubit()
    return q


module.compile(True)
