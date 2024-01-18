from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[bool]) -> int:
    x = 5
    for x in xs:
        pass
    return x
