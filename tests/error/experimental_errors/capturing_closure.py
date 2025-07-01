from guppylang.decorator import guppy


@guppy
def main() -> None:
    x = 42

    def inner() -> int:
        return x


guppy.compile(main)
