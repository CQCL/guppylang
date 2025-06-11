from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: T) -> T:
    ...


@guppy
def main(x: bool) -> None:
    y: None = foo(foo(foo(x)))


guppy.compile(main)
