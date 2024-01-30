from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int]) -> None:
    [y := x for x in xs]
