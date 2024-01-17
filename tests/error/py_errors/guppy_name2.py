from guppylang.decorator import guppy


x = 42


@guppy(compile=True)
def foo(x: int) -> int:
    return py(x + 1)
