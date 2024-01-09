from guppy.decorator import guppy


@guppy
def foo(x: bool, a: int) -> int:
    y = 3
    (y := False) if x or a > 5 else 0
    z = y
    return 42
