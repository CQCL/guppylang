from tests.error.util import guppy, qubit


@guppy
def foo(q: qubit) -> qubit:
    def bar() -> qubit:
        return q

    return q

