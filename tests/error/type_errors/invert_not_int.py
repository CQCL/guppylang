from guppy.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    return ~True
