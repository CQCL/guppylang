from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: int) -> int:
    return foo(True)
