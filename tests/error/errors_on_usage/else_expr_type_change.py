from guppy.decorator import guppy


@guppy
def foo(x: bool) -> int:
    y = 3
    (y := y + 1) if x else (y := True)
    return y
