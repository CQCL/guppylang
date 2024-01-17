from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    return 0
    x = 42
