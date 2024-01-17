from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    while x:
        _@functional
        while x:
            pass
    return 0
