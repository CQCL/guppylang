from tests.error.util import guppy, qubit


@guppy
def foo(q: qubit) -> int:
    x = q
    return 42
