from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> bool:
    return 42
