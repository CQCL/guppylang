from guppy.compiler import GuppyModule
from tests.error.util import guppy, qubit


module = GuppyModule("test")


@module.declare
def new_qubit() -> qubit:
    pass


@module.declare
def measure() -> bool:
    pass


@module
def foo(b: bool) -> bool:
    q = new_qubit()
    if b:
        return measure(q)
    return False


module.compile(True)
