from guppylang import guppy
from guppylang.std.builtins import comptime


@guppy
def main(n: int @comptime) -> None:
    pass


guppy.compile(main)
