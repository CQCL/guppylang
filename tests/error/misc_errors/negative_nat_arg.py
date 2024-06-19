from tests.util import compile_guppy


@compile_guppy
def foo(x: "array[int, -5]") -> None:
    pass
