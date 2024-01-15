from guppy.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    while x:
        continue
        x = 42
