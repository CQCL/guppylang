from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    (y := 1) if x else 0
    return y
