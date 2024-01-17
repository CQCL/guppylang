from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> None:
    y = True if x else 42
