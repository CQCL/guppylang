from guppy.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    a, b, c = 1, True
    return a
