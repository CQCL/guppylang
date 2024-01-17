from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool):
    return x
