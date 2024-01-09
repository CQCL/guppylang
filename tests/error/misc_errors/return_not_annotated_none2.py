from guppy.decorator import guppy


@guppy
def foo():
    def bar(x: int) -> int:
        return x
