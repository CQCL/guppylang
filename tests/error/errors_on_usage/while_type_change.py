from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    y = 5
    while x:
        y = True
    return y
