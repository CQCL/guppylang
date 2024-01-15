from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    if x:
        return 4
    else:
        return 1
    x = 42
