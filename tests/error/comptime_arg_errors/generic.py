from guppylang import guppy
from guppylang.std.builtins import comptime

T = guppy.type_var("T")


@guppy
def main(q: T @comptime) -> None:
    pass


guppy.compile(main)
