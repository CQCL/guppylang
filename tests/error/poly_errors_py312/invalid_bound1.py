from guppylang.decorator import guppy


@guppy
def main[x: 42]() -> None:
    ...


guppy.compile(main)
