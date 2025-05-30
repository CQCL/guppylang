from guppylang.decorator import guppy
from guppylang.std.builtins import array


@guppy
def main() -> None:
    xs = array()


guppy.compile(main)