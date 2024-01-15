from guppy.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    return py(1 / 0)
