from guppylang.decorator import guppy


@guppy
def foo(x: bool) -> int:
    _@functional
    while x:
        if x:
            continue
    return 0
