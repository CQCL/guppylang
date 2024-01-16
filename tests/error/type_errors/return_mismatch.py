from guppy.decorator import guppy


@guppy
def foo() -> bool:
    return 42
