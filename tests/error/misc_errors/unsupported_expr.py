from guppylang.std.builtins import array
from tests.util import compile_guppy


@compile_guppy
def foo(xs: array[int, 1]) -> tuple[int, int]:
    return 0, *xs
