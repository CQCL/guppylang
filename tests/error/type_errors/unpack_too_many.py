from guppy.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    a, b = 1, True, 3.0
    return a
