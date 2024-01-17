from collections.abc import Callable

from guppylang.decorator import guppy


@guppy(compile=True)
def foo() -> Callable[[int], int]:
    def bar(x: int) -> bool:
        return x > 0

    return bar
