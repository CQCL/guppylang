from tests.error.util import guppy, qubit


@guppy
def foo(q: qubit) -> tuple[qubit, qubit]:
    return q, q
