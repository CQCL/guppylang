from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    while x:
        return 42
        x = 42
