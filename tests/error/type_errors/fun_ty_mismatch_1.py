from collections.abc import Callable

from guppy.decorator import guppy


@guppy
def foo() -> Callable[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
