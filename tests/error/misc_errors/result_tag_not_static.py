from guppylang.prelude.builtins import result
from tests.util import compile_guppy


@compile_guppy
def foo(x: int, y: bool) -> None:
    result(x, y)
