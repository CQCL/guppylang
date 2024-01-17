from guppylang.decorator import guppy


@guppy(compile=True)
def foo(x: bool) -> int:
    y = 3
    (y := y + 1) if x else (y := True)
    return y
