from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool, y) -> int:
    return y
