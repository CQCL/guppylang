from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> int:
    for x in xs:
        pass
    return x
