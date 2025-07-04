from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> None:
    ...


@guppy
def main(x: float) -> None:
    f = foo[int]
    f(x)


guppy.compile(main)
