from guppylang.decorator import guppy


@guppy
def main[I: int]() -> None:
    pass


main.compile()
