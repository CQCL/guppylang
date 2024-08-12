from guppylang.prelude.builtins import result
from tests.util import compile_guppy


@compile_guppy
def foo(y: bool) -> None:
    result("foo" + "bar", y)
