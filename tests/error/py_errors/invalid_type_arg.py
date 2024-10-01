from guppylang import py
from guppylang.prelude.builtins import array
from tests.util import compile_guppy


@compile_guppy
def foo(xs: array[int, py(1.0)]) -> None:
    pass
