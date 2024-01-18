from guppylang.decorator import guppy


@compile_guppy
def foo(x: bool) -> int:
    _@functional
    while x:
        _@functional
        while x:
            pass
    return 0
