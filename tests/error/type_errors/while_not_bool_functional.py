from guppylang.decorator import guppy


@compile_guppy
def foo() -> int:
    _@functional
    while 42:
        pass
    return 0
