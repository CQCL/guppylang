from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    _@functional
    while 42:
        pass
    return 0
