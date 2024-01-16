from guppy.decorator import guppy


@guppy
def foo(xs: list[int]) -> None:
    [x for x in xs if x < 5 and x != 6]
