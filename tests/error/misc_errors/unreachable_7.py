from tests.util import compile_guppy


@compile_guppy
def foo() -> int:
    if True:
        return 1
    return 0
