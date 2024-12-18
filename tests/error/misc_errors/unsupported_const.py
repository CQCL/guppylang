from guppylang.std.builtins import array
from tests.util import compile_guppy


@compile_guppy
def foo() -> None:
    x = "foo"
