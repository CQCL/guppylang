from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> None:
    [x for x in xs if x < 5 and x != 6]
