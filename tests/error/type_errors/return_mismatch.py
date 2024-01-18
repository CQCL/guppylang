from tests.util import compile_guppy


@compile_guppy
def foo() -> bool:
    return 42
