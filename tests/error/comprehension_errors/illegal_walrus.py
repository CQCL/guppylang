from guppylang.decorator import guppy


@guppy
def foo(xs: list[int]) -> None:
    [y := x for x in xs]
