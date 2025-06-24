from guppylang.decorator import guppy


@guppy
def main[*Ts]() -> None:
    ...


guppy.compile(main)
