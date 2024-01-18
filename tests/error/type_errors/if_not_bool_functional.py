from guppylang.decorator import guppy


@compile_guppy
def foo() -> int:
    _@functional
    if 42:
        return 0
    return 1
