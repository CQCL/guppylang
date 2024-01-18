from tests.util import compile_guppy


@compile_guppy
def foo():
    def bar(x: int) -> int:
        return x
