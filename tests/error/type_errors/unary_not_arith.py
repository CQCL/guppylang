from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    return -True
