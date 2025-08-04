from guppylang.decorator import guppy


@guppy
def x() -> None:
    pass

@guppy
def bad(b: bool) -> int:
    if b:
        x = 4
    return x

bad.compile()
