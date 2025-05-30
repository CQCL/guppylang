from guppylang.decorator import guppy


@guppy
def main(x: list[int]) -> list[int]:
    return x


guppy.compile(main)
