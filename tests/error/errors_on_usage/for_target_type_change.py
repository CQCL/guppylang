from tests.error.util import guppy


@guppy
def foo(xs: list[bool]) -> int:
    x = 5
    for x in xs:
        pass
    return x
