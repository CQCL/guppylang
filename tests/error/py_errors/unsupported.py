from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> int:
    return py({1, 2, 3})
