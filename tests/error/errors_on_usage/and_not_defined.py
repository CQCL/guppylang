from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool, y: int) -> int:
    if x and (z := y + 1):
        return z
    else:
        return z
