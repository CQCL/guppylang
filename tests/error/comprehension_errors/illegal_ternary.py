from tests.util import compile_guppy


@compile_guppy
def foo(xs: list[int], ys: list[int], b: bool) -> None:
    [x for x in (xs if b else ys)]
