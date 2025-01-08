from guppylang.std.builtins import panic
from tests.util import compile_guppy


@compile_guppy
def foo(y: bool) -> None:
    panic("foo" if y else "bar", y)
