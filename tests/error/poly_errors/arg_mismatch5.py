from guppylang.decorator import guppy


@guppy
def main(x: list[42]) -> None:
    pass


guppy.compile(main)
