from tests.util import compile_guppy


@compile_guppy
def foo(x: bool, a: int) -> int:
    y = 3
    (y := False) if x or a > 5 else 0
    z = y
    return 42
