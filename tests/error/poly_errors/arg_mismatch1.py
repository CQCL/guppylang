from guppylang.decorator import guppy

T = guppy.type_var("T")


@guppy.declare
def foo(x: T, y: T) -> None:
    ...


@guppy
def main(x: bool, y: tuple[bool]) -> None:
    foo(x, y)


guppy.compile(main)
