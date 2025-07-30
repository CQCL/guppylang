from guppylang import guppy
from guppylang.std.builtins import comptime

T = guppy.type_var("T", copyable=True, droppable=True)


@guppy
def foo(q: T @comptime) -> T:
    return T


@guppy
def main() -> int:
    return foo(42)


guppy.compile(main)
