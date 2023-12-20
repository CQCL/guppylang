from tests.error.util import guppy


@guppy
def foo(xs: list[int]) -> int:
    for x in xs:
        pass
    return x
