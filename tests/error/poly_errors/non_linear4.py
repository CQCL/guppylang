from guppylang.decorator import guppy
from guppylang.std.quantum import qubit

T = guppy.type_var("T", copyable=False, droppable=True)


@guppy.declare
def foo(x: T) -> None:
    ...


@guppy
def main(q: qubit) -> None:
    foo(q)


guppy.compile(main)
