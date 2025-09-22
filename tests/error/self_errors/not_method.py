from guppylang.decorator import guppy


@guppy
def foo(self) -> None:
    pass


@guppy
def main() -> None:
    foo(42)


guppy.compile(main)