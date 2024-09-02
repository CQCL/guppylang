from tests.util import compile_guppy


@compile_guppy
def f(x: "foo.bar") -> None:
    return
